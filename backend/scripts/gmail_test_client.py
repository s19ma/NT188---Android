"""One registration attempt; retains the generated password in memory only."""
import os
import secrets
import sys
import time
import requests
from sqlalchemy import select
from app.db.database import engine, SessionLocal
from app.models.user import User
from scripts.gmail_test_server import check_url


def main():
    if not os.environ.get("DATABASE_URL") or not os.environ.get("DIRECT_DATABASE_URL"):
        raise RuntimeError("Explicit local test database URLs required")
    check_url(os.environ["DATABASE_URL"])
    check_url(os.environ["DIRECT_DATABASE_URL"])
    check_url(engine.url.render_as_string(hide_password=False))
    email = os.environ["GMAIL_TEST_RECIPIENT"].strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise RuntimeError("Test account already exists; nothing sent")
    password = secrets.token_urlsafe(24)
    try:
        response = requests.post("http://127.0.0.1:8000/api/v1/users/register",
                                 json={"email": email, "password": password}, timeout=25)
    except requests.RequestException:
        print("WARNING: registration response uncertain; do not retry", flush=True)
        return
    print("Registration HTTP status:", response.status_code, flush=True)
    if response.status_code != 201:
        print("WARNING: no retry will be attempted; SMTP outcome may be uncertain", flush=True)
        return
    print("Waiting for local email verification; password retained only in this process", flush=True)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        with SessionLocal() as db:
            verified = db.scalar(select(User.email_verified).where(User.email == email))
        if verified:
            login = requests.post("http://127.0.0.1:8000/api/v1/users/login", data={"username": email, "password": password}, timeout=15)
            print("Login HTTP status:", login.status_code, flush=True)
            if login.ok:
                token = login.json().get("access_token", "")
                me = requests.get("http://127.0.0.1:8000/api/v1/users/me", headers={"Authorization": "Bearer " + token}, timeout=15)
                print("Authenticated profile HTTP status:", me.status_code, flush=True)
            return
        time.sleep(3)
    print("Verification not completed within the local test window", flush=True)


if __name__ == "__main__":
    main()
