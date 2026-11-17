"""Local-only API/worker process smoke test; email delivery is simulated."""
import json
import os
import subprocess
import sys
import time
import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url


@pytest.fixture
def staging():
    url = make_url(os.environ.get("DATABASE_URL", "sqlite://"))
    direct = make_url(os.environ.get("DIRECT_DATABASE_URL", "sqlite://"))
    for item in (url, direct):
        if (item.get_backend_name() != "postgresql" or item.host != "127.0.0.1"
                or item.port != 5433 or item.database != "english_video_staging_test"
                or item.username != "test_user"):
            pytest.skip("Requires the dedicated local staging database")
    if os.environ.get("EMAIL_DELIVERY_MODE") != "mock" or os.environ.get("APP_ENVIRONMENT") != "development":
        pytest.skip("Only mock email delivery is permitted")
    from app.db.database import Base, engine
    import app.models  # noqa: F401
    from app.models.user import User
    from app.models.password_reset_otp import PasswordResetOtp
    from app.models.email_verification_otp import EmailVerificationOtp
    from app.models.email_outbox import EmailOutbox
    Base.metadata.create_all(engine, tables=[User.__table__, PasswordResetOtp.__table__,
                                            EmailVerificationOtp.__table__, EmailOutbox.__table__])
    from app.main import app
    with TestClient(app) as client:
        yield client


def test_registration_and_reset_with_separate_mock_worker(staging):
    from app.db.database import SessionLocal
    from app.models.email_outbox import EmailOutbox
    cipher = Fernet(os.environ["EMAIL_OUTBOX_ENCRYPTION_KEY"].encode())
    email = f"stage_{uuid.uuid4().hex}@example.com"

    def read_job():
        with SessionLocal() as db:
            jobs = db.scalars(select(EmailOutbox).where(EmailOutbox.status == "pending")).all()
            matches = [(job.id, json.loads(cipher.decrypt(bytes(job.ciphertext)))) for job in jobs]
            matching = [(job_id, payload) for job_id, payload in matches if payload["email"] == email]
            assert len(matching) == 1
            return matching[0][0], matching[0][1]["code"]

    def run_worker(job_id):
        worker = subprocess.Popen([sys.executable, "-m", "scripts.email_outbox_worker"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                with SessionLocal() as db:
                    job = db.get(EmailOutbox, job_id)
                    if job.status == "sent":
                        assert job.ciphertext is None
                        return
                if worker.poll() is not None:
                    pytest.fail("Worker exited before processing job")
                time.sleep(.1)
            pytest.fail("Worker did not process job in time")
        finally:
            worker.terminate()
            worker.wait(timeout=10)

    assert staging.post("/api/v1/users/register", json={"email": email, "password": "oldpassword123"}).status_code == 201
    job_id, code = read_job()
    run_worker(job_id)
    assert staging.post("/api/v1/auth/email-verification/confirm", json={"email": email, "code": code}).status_code == 200
    login = staging.post("/api/v1/users/login", data={"username": email, "password": "oldpassword123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert staging.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert staging.post("/api/v1/auth/password-reset/request", json={"email": email}).status_code == 200
    job_id, code = read_job()
    run_worker(job_id)
    assert staging.post("/api/v1/auth/password-reset/confirm", json={"email": email, "code": code, "password": "newpassword123"}).status_code == 200
    assert staging.post("/api/v1/users/login", data={"username": email, "password": "newpassword123"}).status_code == 200
