import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.database import get_db
from app.models.password_reset_otp import PasswordResetOtp
from app.models.email_verification_otp import EmailVerificationOtp
from app.models.user import User
from app.services import email_sender
from app.services.email_outbox import enqueue, require_no_inflight_delivery
from app.schemas.auth import (
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetVerify,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
MAX_ATTEMPTS = 5


def _allow_send(otp, now):
    if otp is None:
        return now, 1
    if otp.created_at > now - timedelta(seconds=max(60, settings.otp_resend_cooldown_seconds)):
        raise HTTPException(status_code=429, detail="Please wait before requesting another code.")
    if otp.window_started_at <= now - timedelta(hours=1):
        return now, 1
    if otp.send_count >= settings.otp_max_sends_per_hour:
        raise HTTPException(status_code=429, detail="Please wait before requesting another code.")
    return otp.window_started_at, otp.send_count + 1


def send_verification_code(user: User, db: Session) -> None:
    now = datetime.now(timezone.utc)
    otp = db.scalar(select(EmailVerificationOtp).where(EmailVerificationOtp.user_id == user.id).with_for_update())
    window, send_count = _allow_send(otp, now)
    if otp is not None:
        require_no_inflight_delivery(db, otp.code_hash)
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = hash_password(code)
    enqueue(db, user.email, code, "verify your email", settings.email_verification_otp_expire_minutes, code_hash, now)
    if otp is None:
        otp = EmailVerificationOtp(user_id=user.id, code_hash=code_hash,
            expires_at=now + timedelta(minutes=settings.email_verification_otp_expire_minutes), created_at=now, attempts=0,
            window_started_at=window, send_count=send_count)
        db.add(otp)
    else:
        otp.code_hash = code_hash
        otp.expires_at = now + timedelta(minutes=settings.email_verification_otp_expire_minutes)
        otp.created_at = now
        otp.attempts = 0
        otp.window_started_at = window
        otp.send_count = send_count


@router.post("/email-verification/resend", response_model=MessageResponse)
def resend_verification(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    email_sender.ensure_available()
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email).with_for_update())
    if user and user.is_active and not user.email_verified:
        send_verification_code(user, db)
        db.commit()
    return MessageResponse(message="If verification is needed, a code will be sent.")


@router.post("/email-verification/confirm", response_model=MessageResponse)
def confirm_verification(payload: PasswordResetVerify, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email).with_for_update())
    otp = db.scalar(select(EmailVerificationOtp).where(EmailVerificationOtp.user_id == user.id).with_for_update()) if user else None
    if not user or not user.is_active or user.email_verified or not otp or otp.expires_at <= datetime.now(timezone.utc) or otp.attempts >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
    otp.attempts += 1
    if not verify_password(payload.code, otp.code_hash):
        db.commit()
        raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
    user.email_verified = True
    db.delete(otp)
    db.commit()
    return MessageResponse(message="Email verified. Please sign in.")


@router.post("/password-reset/request", response_model=MessageResponse)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    email_sender.ensure_available()
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email).with_for_update())
    # Do not reveal whether an account exists. Do not persist an OTP without email delivery.
    if not user:
        return MessageResponse(message="If the account is eligible, the request will be processed.")

    recent = db.scalar(select(PasswordResetOtp).where(PasswordResetOtp.email == email)
                       .order_by(PasswordResetOtp.created_at.desc()).limit(1).with_for_update())
    now = datetime.now(timezone.utc)
    try:
        window, send_count = _allow_send(recent, now)
        if recent is not None:
            require_no_inflight_delivery(db, recent.code_hash)
    except HTTPException as error:
        if error.status_code != 429: raise
        return MessageResponse(message="If the account is eligible, the request will be processed.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = hash_password(code)
    enqueue(db, email, code, "password reset", settings.password_reset_otp_expire_minutes, code_hash, now)
    db.execute(delete(PasswordResetOtp).where(PasswordResetOtp.email == email))
    db.add(
        PasswordResetOtp(
            email=email,
            code_hash=code_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.password_reset_otp_expire_minutes),
            window_started_at=window,
            send_count=send_count,
        )
    )
    db.commit()
    return MessageResponse(message="If the account is eligible, the request will be processed.")


def _validate_otp(payload: PasswordResetVerify, db: Session) -> PasswordResetOtp:
    email = payload.email.strip().lower()
    otp = db.scalar(
        select(PasswordResetOtp)
        .where(PasswordResetOtp.email == email, PasswordResetOtp.consumed_at.is_(None))
        .order_by(PasswordResetOtp.created_at.desc())
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if not otp or otp.expires_at <= now or otp.attempts >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
    otp.attempts += 1
    if not verify_password(payload.code, otp.code_hash):
        db.commit()
        raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
    return otp


@router.post("/password-reset/verify", response_model=MessageResponse)
def verify_password_reset(payload: PasswordResetVerify, db: Session = Depends(get_db)):
    _validate_otp(payload, db)
    db.rollback()  # Verification itself must not consume the one-time code.
    return MessageResponse(message="Verification code accepted.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    otp = _validate_otp(payload, db)
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
    if not user:
        raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
    user.password_hash = hash_password(payload.password)
    otp.consumed_at = datetime.now(timezone.utc)
    db.commit()
    return MessageResponse(message="Password has been reset. Please sign in again.")
