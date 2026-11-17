import threading
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from sqlalchemy import select
from app.db.database import engine, SessionLocal
from app.models.user import User
from app.models.email_verification_otp import EmailVerificationOtp
from app.models.email_outbox import EmailOutbox
from app.services import email_outbox, email_sender


@pytest.fixture(autouse=True)
def isolated_database():
    u=engine.url
    if u.host not in ("localhost","127.0.0.1") or u.port != 5433 or u.database != "english_video_test" or u.username != "test_user":
        pytest.skip("Only the isolated Docker database is permitted")


def make_job():
    now=datetime.now(timezone.utc)
    marker=uuid.uuid4().hex
    with SessionLocal() as db, patch.object(email_sender, "ensure_available"):
        user=User(id=uuid.uuid4(), email=f"outbox_{uuid.uuid4().hex}@example.com", password_hash="hash", email_verified=False)
        db.add(user); db.flush()
        db.add(EmailVerificationOtp(user_id=user.id,code_hash=marker,expires_at=now+timedelta(minutes=5),created_at=now,window_started_at=now,send_count=1,attempts=0))
        email_outbox.enqueue(db,user.email,"123456","verify your email",5,marker,now)
        db.flush()
        job=db.scalar(select(EmailOutbox).where(EmailOutbox.otp_hash==marker))
        job.created_at=now-timedelta(days=1000); db.commit()
        return job.id


def test_commit_rollback_does_not_queue():
    now=datetime.now(timezone.utc)
    marker=f"rollback-{uuid.uuid4().hex}"
    with SessionLocal() as db, patch.object(email_sender,"ensure_available"):
        email_outbox.enqueue(db,"test@example.com","123456","verify your email",5,marker,now)
        db.flush(); db.rollback()
        assert db.scalar(select(EmailOutbox.id).where(EmailOutbox.otp_hash==marker)) is None


def test_encrypted_job_and_worker_success():
    job_id=make_job()
    with SessionLocal() as db:
        job=db.get(EmailOutbox,job_id)
        assert b"123456" not in bytes(job.ciphertext)
        with patch.object(email_sender,"send_otp") as sender:
            assert email_outbox.process_one(db,job_id=job_id)
        sender.assert_called_once()
        assert db.get(EmailOutbox,job_id).status=="sent"
        assert db.get(EmailOutbox,job_id).ciphertext is None


def test_wrong_worker_key_preserves_pending_job_for_recovery():
    from cryptography.fernet import Fernet
    from pydantic import SecretStr
    from app.core.config import settings
    job_id=make_job()
    with SessionLocal() as db:
        original=bytes(db.get(EmailOutbox,job_id).ciphertext)
        with patch.object(settings,"email_outbox_encryption_key",SecretStr(Fernet.generate_key().decode())):
            with pytest.raises(RuntimeError,match="cannot be decrypted"):
                email_outbox.process_one(db,job_id=job_id)
        job=db.get(EmailOutbox,job_id)
        assert job.status=="pending" and bytes(job.ciphertext)==original
        with patch.object(email_sender,"send_otp") as sender:
            assert email_outbox.process_one(db,job_id=job_id)
        sender.assert_called_once()
        assert db.get(EmailOutbox,job_id).status=="sent"


def test_timeout_after_smtp_send_is_uncertain_not_retried():
    job_id=make_job()
    with SessionLocal() as db, patch.object(email_sender,"send_otp",side_effect=email_sender.DeliveryError(False)):
        assert email_outbox.process_one(db,job_id=job_id)
        job=db.get(EmailOutbox,job_id)
        assert job.status=="uncertain" and job.ciphertext is None


def test_connection_failure_before_send_gets_backoff():
    job_id=make_job()
    with SessionLocal() as db, patch.object(email_sender,"send_otp",side_effect=email_sender.DeliveryError(True)):
        assert email_outbox.process_one(db,job_id=job_id)
        job=db.get(EmailOutbox,job_id)
        assert job.status=="pending" and job.attempts==1 and job.available_at > datetime.now(timezone.utc)


def test_abandoned_claim_is_uncertain():
    job_id=make_job(); now=datetime.now(timezone.utc)
    with SessionLocal() as db:
        job=db.get(EmailOutbox,job_id); job.status="sending"; job.claimed_at=now-timedelta(minutes=2); db.commit()
        email_outbox.mark_abandoned(db,now)
        assert db.get(EmailOutbox,job_id).status=="uncertain"


def test_two_workers_do_not_claim_same_job():
    job_id=make_job(); started=threading.Event(); release=threading.Event(); sends=[]
    def send(*args):
        sends.append(1); started.set(); release.wait(5)
    def worker():
        with SessionLocal() as db: email_outbox.process_one(db,job_id=job_id)
    with patch.object(email_sender,"send_otp",side_effect=send):
        first=threading.Thread(target=worker); first.start(); assert started.wait(5)
        second=threading.Thread(target=worker); second.start(); second.join(5)
        assert not second.is_alive()
        with SessionLocal() as db:
            job=db.get(EmailOutbox,job_id)
            assert job.status=="sending"
        release.set(); first.join(5)
    assert not first.is_alive() and len(sends)==1


def test_resend_is_rejected_while_prior_code_is_sending():
    from fastapi.testclient import TestClient
    from app.main import app
    job_id=make_job(); started=threading.Event(); release=threading.Event()
    with SessionLocal() as db:
        job=db.get(EmailOutbox,job_id)
        otp=db.scalar(select(EmailVerificationOtp).where(EmailVerificationOtp.code_hash==job.otp_hash))
        user=db.get(User,otp.user_id); email=user.email
        otp.created_at=datetime.now(timezone.utc)-timedelta(seconds=61); db.commit()
    def send(*args): started.set(); release.wait(5)
    def worker():
        with SessionLocal() as db: email_outbox.process_one(db,job_id=job_id)
    with patch.object(email_sender,"send_otp",side_effect=send), patch.object(email_sender,"ensure_available"):
        first=threading.Thread(target=worker); first.start()
        try:
            assert started.wait(5)
            with TestClient(app) as client:
                response=client.post("/api/v1/auth/email-verification/resend",json={"email":email})
            assert response.status_code==429
        finally:
            release.set(); first.join(5)
    assert not first.is_alive()
