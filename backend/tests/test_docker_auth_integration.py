"""Integration checks: only run against the dedicated local Docker test database."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.db.database import engine, SessionLocal
from app.main import app
from app.models.user import User
from app.models.password_reset_otp import PasswordResetOtp
from app.models.email_verification_otp import EmailVerificationOtp
from app.models.email_outbox import EmailOutbox
from app.services import email_outbox
from app.core.security import hash_password


@pytest.fixture
def test_client():
    url = engine.url
    if url.host not in ("127.0.0.1", "localhost") or url.port != 5433 or url.database != "english_video_test" or url.username != "test_user":
        pytest.skip("Requires the explicitly isolated local Docker test database")
    with TestClient(app) as client:
        yield client


def test_registration_and_password_reset(test_client):
    email = f"api_test_{uuid.uuid4().hex}@example.com"
    sent = []
    def mock_send(recipient, code, purpose, minutes):
        sent.append((recipient, code, purpose))
    original_enqueue = email_outbox.enqueue
    def capture_enqueue(db, recipient, code, purpose, minutes, otp_hash, now):
        mock_send(recipient, code, purpose, minutes)
        return original_enqueue(db, recipient, code, purpose, minutes, otp_hash, now)
    with patch("app.api.v1.endpoints.auth.enqueue", side_effect=capture_enqueue), patch("app.services.email_sender.ensure_available"):
        response = test_client.post("/api/v1/users/register", json={"email": email, "password": "oldpassword123"})
        assert response.status_code == 201
        assert len(sent) == 1 and sent[0][1] not in response.text
        registration_code = sent[0][1]
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None and not user.email_verified
            otp = db.get(EmailVerificationOtp, user.id)
            assert otp.code_hash != registration_code
        assert test_client.post("/api/v1/users/login", data={"username": email, "password": "oldpassword123"}).status_code == 403
        assert test_client.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": "not-otp"}).status_code == 422
        assert test_client.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": registration_code}).status_code == 200
        assert test_client.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": registration_code}).status_code == 400
        assert test_client.post("/api/v1/users/login", data={"username": email, "password": "oldpassword123"}).status_code == 200
        response = test_client.post("/api/v1/auth/password-reset/request", json={"email": email})
        assert response.status_code == 200 and len(sent) == 2
        reset_code = sent[-1][1]
        assert reset_code not in response.text
        with SessionLocal() as db:
            otp = db.scalar(select(PasswordResetOtp).where(PasswordResetOtp.email == email))
            assert otp.code_hash != reset_code
        assert test_client.post("/api/v1/auth/password-reset/confirm", json={"email": email, "code": reset_code, "password": "newpassword123"}).status_code == 200
        assert test_client.post("/api/v1/auth/password-reset/confirm", json={"email": email, "code": reset_code, "password": "newpassword123"}).status_code == 400
        assert test_client.post("/api/v1/users/login", data={"username": email, "password": "oldpassword123"}).status_code == 401
        assert test_client.post("/api/v1/users/login", data={"username": email, "password": "newpassword123"}).status_code == 200


def test_reset_unknown_email_is_generic(test_client):
    with patch("app.services.email_sender.ensure_available"), patch("app.services.email_sender.send_otp") as sender:
        response = test_client.post("/api/v1/auth/password-reset/request", json={"email": f"missing_{uuid.uuid4().hex}@example.com"})
    assert response.status_code == 200
    sender.assert_not_called()


def test_registration_delivery_failure_rolls_back(test_client):
    email = f"api_test_{uuid.uuid4().hex}@example.com"
    with patch("app.api.v1.endpoints.auth.enqueue", side_effect=HTTPException(status_code=503, detail="delivery failed")):
        response = test_client.post("/api/v1/users/register", json={"email": email, "password": "oldpassword123"})
    assert response.status_code == 503
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == email)) is None


def test_registration_commit_failure_does_not_persist_user_or_job(test_client):
    email=f"api_test_{uuid.uuid4().hex}@example.com"
    with SessionLocal() as db:
        before=len(db.scalars(select(EmailOutbox.id)).all())
    with patch("app.services.email_sender.ensure_available"), patch.object(Session,"commit",side_effect=RuntimeError("simulated commit failure")):
        with TestClient(app, raise_server_exceptions=False) as client:
            response=client.post("/api/v1/users/register",json={"email":email,"password":"oldpassword123"})
    assert response.status_code==500
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(User.email==email)) is None
        assert len(db.scalars(select(EmailOutbox.id)).all())==before


def test_wrong_and_expired_registration_codes(test_client):
    email = f"api_test_{uuid.uuid4().hex}@example.com"
    sent = []
    original_enqueue = email_outbox.enqueue
    def capture_enqueue(db, recipient, code, purpose, minutes, otp_hash, now):
        sent.append(code)
        return original_enqueue(db, recipient, code, purpose, minutes, otp_hash, now)
    with patch("app.api.v1.endpoints.auth.enqueue", side_effect=capture_enqueue), patch("app.services.email_sender.ensure_available"):
        assert test_client.post("/api/v1/users/register", json={"email": email, "password": "oldpassword123"}).status_code == 201
        bad = "000000" if sent[0] != "000000" else "111111"
        for _ in range(5):
            assert test_client.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": bad}).status_code == 400
        assert test_client.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": sent[0]}).status_code == 400
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            otp = db.get(EmailVerificationOtp, user.id)
            otp.attempts = 0
            otp.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        assert test_client.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": sent[0]}).status_code == 400


def test_concurrent_resend_is_rate_limited(test_client):
    email = f"api_test_{uuid.uuid4().hex}@example.com"
    with patch("app.services.email_sender.ensure_available"):
        assert test_client.post("/api/v1/users/register", json={"email": email, "password": "oldpassword123"}).status_code == 201
        with SessionLocal() as db:
            user=db.scalar(select(User).where(User.email==email))
            otp=db.get(EmailVerificationOtp,user.id)
            otp.created_at=datetime.now(timezone.utc)-timedelta(seconds=61)
            db.commit()
        def resend():
            return test_client.post("/api/v1/auth/email-verification/resend",json={"email":email}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(lambda _:resend(),range(2)))
        assert sorted(statuses)==[200,429]


def test_existing_verified_account_can_login(test_client):
    email=f"legacy_{uuid.uuid4().hex}@example.com"
    with SessionLocal() as db:
        db.add(User(email=email,password_hash=hash_password("oldpassword123")))
        db.commit()
    assert test_client.post("/api/v1/users/login",data={"username":email,"password":"oldpassword123"}).status_code==200
