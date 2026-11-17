"""Encrypted OTP outbox: enqueue in caller transaction; SMTP in a separate worker."""
import json
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models.email_outbox import EmailOutbox
from app.models.email_verification_otp import EmailVerificationOtp
from app.models.password_reset_otp import PasswordResetOtp
from app.models.user import User
from app.services import email_sender


def _cipher():
    try:
        return Fernet(settings.email_outbox_encryption_key.get_secret_value().encode())
    except (AttributeError, ValueError, TypeError):
        raise HTTPException(status_code=503, detail="Email delivery is not configured.")


def enqueue(db, email, code, purpose, minutes, otp_hash, now):
    email_sender.ensure_available()
    payload = json.dumps({"email": email, "code": code, "purpose": purpose, "minutes": minutes}).encode()
    job = EmailOutbox(ciphertext=_cipher().encrypt(payload), otp_hash=otp_hash,
                      expires_at=now + timedelta(minutes=minutes))
    db.add(job)


def require_no_inflight_delivery(db, otp_hash):
    """Called while holding the OTP row lock; the worker takes that same lock."""
    if otp_hash and db.scalar(select(EmailOutbox.id).where(
            EmailOutbox.otp_hash == otp_hash, EmailOutbox.status == "sending").limit(1)) is not None:
        raise HTTPException(status_code=429, detail="Please wait before requesting another code.")


def mark_abandoned(db, now, after_seconds=60):
    """A worker may have sent before it crashed: do not retry ambiguous jobs."""
    jobs = db.scalars(select(EmailOutbox).where(EmailOutbox.status == "sending",
        EmailOutbox.claimed_at < now - timedelta(seconds=after_seconds)).with_for_update(skip_locked=True)).all()
    for job in jobs:
        job.status = "uncertain"
        job.last_error = "worker interrupted during delivery"
        job.ciphertext = None
    db.commit()
    return len(jobs)


def process_one(db, now=None, job_id=None):
    now = now or datetime.now(timezone.utc)
    query = select(EmailOutbox).where(EmailOutbox.status == "pending", EmailOutbox.available_at <= now)
    if job_id is not None:
        query = query.where(EmailOutbox.id == job_id)
    job = db.scalar(query.order_by(EmailOutbox.created_at).limit(1).with_for_update(skip_locked=True))
    if job is None:
        db.rollback()
        return False
    if job.expires_at <= now or not job.ciphertext:
        job.status = "expired"; job.ciphertext = None; db.commit(); return True
    try:
        payload = json.loads(_cipher().decrypt(bytes(job.ciphertext)))
    except (InvalidToken, ValueError, TypeError, HTTPException) as error:
        # A missing or incorrect worker key must never destroy recoverable jobs.
        # Leave the job pending, release its lock, and let monitoring alert on age.
        db.rollback()
        raise RuntimeError("Email outbox payload cannot be decrypted") from error
    if payload["purpose"] == "verify your email":
        current = db.scalar(select(EmailVerificationOtp).join(User, User.id == EmailVerificationOtp.user_id)
                            .where(User.email == payload["email"]).with_for_update(of=EmailVerificationOtp))
    elif payload["purpose"] == "password reset":
        current = db.scalar(select(PasswordResetOtp).where(PasswordResetOtp.email == payload["email"],
                            PasswordResetOtp.consumed_at.is_(None)).order_by(PasswordResetOtp.created_at.desc()).limit(1)
                            .with_for_update(of=PasswordResetOtp))
    else:
        current = None
    if current is None or current.code_hash != job.otp_hash or current.expires_at <= now:
        job.status = "superseded"; job.ciphertext = None; db.commit(); return True
    job.status = "sending"; job.claimed_at = now; job.attempts += 1
    job_id = job.id
    db.commit()  # Durable claim before external SMTP; never hold a database lock during delivery.
    if datetime.now(timezone.utc) >= job.expires_at:
        job = db.get(EmailOutbox, job_id)
        if job is not None and job.status == "sending":
            job.status = "expired"; job.ciphertext = None; db.commit()
        else: db.rollback()
        return True
    try:
        email_sender.send_otp(payload["email"], payload["code"], payload["purpose"], payload["minutes"])
    except email_sender.DeliveryError as error:
        job = db.get(EmailOutbox, job_id)
        if job is None or job.status != "sending":
            db.rollback(); return True
        if error.retryable and job.attempts < 3 and job.expires_at > datetime.now(timezone.utc) + timedelta(seconds=30):
            job.status = "pending"
            job.available_at = datetime.now(timezone.utc) + timedelta(seconds=30 * (2 ** (job.attempts - 1)))
        else:
            job.status = "uncertain" if not error.retryable else "failed"
            job.ciphertext = None
        job.last_error = "delivery failed before sending" if error.retryable else "delivery outcome uncertain"
        db.commit(); return True
    except Exception:
        job = db.get(EmailOutbox, job_id)
        if job is not None and job.status == "sending":
            job.status = "uncertain"; job.last_error = "delivery outcome uncertain"; job.ciphertext = None; db.commit()
        else: db.rollback()
        return True
    job = db.get(EmailOutbox, job_id)
    if job is not None and job.status == "sending":
        job.status = "sent"; job.ciphertext = None; job.last_error = None; db.commit()
    else: db.rollback()
    return True
