"""Run a one-recipient, one-send local SMTP test after rotating the SMTP key.

Supply DATABASE_URL, DIRECT_DATABASE_URL, EMAIL_DELIVERY_MODE=smtp and
GMAIL_TEST_RECIPIENT to this process. Never use this launcher in production.
"""
import os
import threading
from urllib.parse import urlsplit

from sqlalchemy import text
import uvicorn

from app.core.config import settings
from app.db.database import engine
from app.main import app
from app.services import email_sender


def check_url(raw):
    parsed = urlsplit(raw.replace("postgresql+psycopg://", "postgresql://", 1))
    if (parsed.scheme != "postgresql" or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.port != 5433 or parsed.path != "/english_video_test"
            or parsed.username != "test_user" or parsed.query or parsed.fragment):
        raise RuntimeError("Database configuration is not the isolated Docker test target")


def main():
    if not os.environ.get("DATABASE_URL") or not os.environ.get("DIRECT_DATABASE_URL"):
        raise RuntimeError("Both test database URLs must be explicitly supplied to this process")
    check_url(os.environ["DATABASE_URL"])
    check_url(os.environ["DIRECT_DATABASE_URL"])
    check_url(settings.database_url)
    check_url(settings.direct_database_url)
    check_url(engine.url.render_as_string(hide_password=False))
    recipient = os.environ.get("GMAIL_TEST_RECIPIENT", "").strip().lower()
    if not recipient or not recipient.endswith("@gmail.com"):
        raise RuntimeError("Set GMAIL_TEST_RECIPIENT to the approved Gmail address")
    if settings.email_delivery_mode != "smtp":
        raise RuntimeError("This test requires explicit smtp mode")
    if settings.smtp_host != "smtp-relay.brevo.com" or settings.smtp_port != 587 or not settings.smtp_use_tls:
        raise RuntimeError("Unexpected SMTP transport configuration")
    email_sender.ensure_available()
    with engine.connect() as connection:
        row = connection.execute(text("SELECT current_database(), current_user, version_num FROM alembic_version")).one()
        if tuple(row) != ("english_video_test", "test_user", "b531d7e28a22"):
            raise RuntimeError("Unexpected database identity or migration revision")
        exists = connection.execute(text("SELECT EXISTS (SELECT 1 FROM users WHERE lower(email)=:email)"), {"email": recipient}).scalar_one()
        if exists:
            raise RuntimeError("Test account already exists; it was not modified")

    original_send = email_sender.send_otp
    guard = threading.Lock()
    attempted = False

    def single_send(address, code, purpose, minutes):
        nonlocal attempted
        with guard:
            if attempted or address.strip().lower() != recipient or purpose != "verify your email":
                raise RuntimeError("Email attempt blocked by the single-send test guard")
            attempted = True  # A timeout may still mean the provider accepted the email.
        return original_send(address, code, purpose, minutes)

    email_sender.send_otp = single_send
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
