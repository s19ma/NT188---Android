import unittest
import smtplib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from fastapi import HTTPException
from pydantic import ValidationError
from app.api.v1.endpoints import auth
from app.core.security import hash_password, verify_password
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest, PasswordResetVerify
from app.schemas.user import UserCreate
from app.services import email_sender
from pydantic import SecretStr


class AuthenticationFlowTests(unittest.TestCase):
    def test_schema_rejects_invalid_email_and_short_password(self):
        with self.assertRaises(ValidationError): UserCreate(email="bad", password="12345678")
        with self.assertRaises(ValidationError): UserCreate(email="test@example.com", password="short")
        with self.assertRaises(ValidationError): PasswordResetConfirm(email="test@example.com", code="123456", password="short")

    def test_otp_hash_does_not_equal_plaintext(self):
        hashed = hash_password("123456")
        self.assertNotEqual(hashed, "123456")
        self.assertTrue(verify_password("123456", hashed))
        self.assertFalse(verify_password("654321", hashed))

    def test_disabled_and_mock_sender(self):
        with patch.object(email_sender.settings, "email_delivery_mode", "disabled"):
            with self.assertRaises(HTTPException): email_sender.send_otp("test@example.com", "123456", "test", 5)
        with patch.object(email_sender.settings, "email_delivery_mode", "mock"), patch.object(email_sender.settings, "app_environment", "development"), patch("smtplib.SMTP") as smtp:
            email_sender.send_otp("test@example.com", "123456", "test", 5)
            smtp.assert_not_called()
        with patch.object(email_sender.settings, "email_delivery_mode", "mock"), patch.object(email_sender.settings, "app_environment", "production"):
            with self.assertRaises(HTTPException): email_sender.ensure_available()

    def test_reset_unknown_email_returns_generic_response(self):
        db=Mock(); db.scalar.return_value=None
        with patch.object(auth.email_sender, "ensure_available"):
            result=auth.request_password_reset(PasswordResetRequest(email="nobody@example.com"),db)
        self.assertNotIn("123456", result.message)
        db.add.assert_not_called()

    def test_invalid_expired_and_exhausted_reset_otp(self):
        payload=PasswordResetVerify(email="test@example.com",code="123456")
        now=datetime.now(timezone.utc)
        for otp in (SimpleNamespace(expires_at=now-timedelta(seconds=1),attempts=0), SimpleNamespace(expires_at=now+timedelta(minutes=1),attempts=5)):
            db=Mock(); db.scalar.return_value=otp
            with self.assertRaises(HTTPException): auth._validate_otp(payload,db)
            db.commit.assert_not_called()
        db=Mock(); otp=SimpleNamespace(expires_at=now+timedelta(minutes=1),attempts=0,code_hash=hash_password("654321")); db.scalar.return_value=otp
        with self.assertRaises(HTTPException): auth._validate_otp(payload,db)
        self.assertEqual(otp.attempts,1); db.commit.assert_called_once()

    def test_reset_changes_password_and_marks_code_consumed(self):
        old_hash=hash_password("oldpassword")
        user=SimpleNamespace(password_hash=old_hash)
        otp=SimpleNamespace(consumed_at=None)
        db=Mock(); db.scalar.return_value=user
        payload=PasswordResetConfirm(email="test@example.com",code="123456",password="newpassword")
        with patch.object(auth, "_validate_otp", return_value=otp): auth.confirm_password_reset(payload,db)
        self.assertTrue(verify_password("newpassword",user.password_hash))
        self.assertFalse(verify_password("oldpassword",user.password_hash))
        self.assertIsNotNone(otp.consumed_at); db.commit.assert_called_once()

    def test_send_limit_and_window_reset(self):
        now=datetime.now(timezone.utc)
        otp=SimpleNamespace(created_at=now-timedelta(minutes=2),window_started_at=now-timedelta(minutes=30),send_count=5)
        with self.assertRaises(HTTPException): auth._allow_send(otp,now)
        otp.window_started_at=now-timedelta(hours=2)
        self.assertEqual(auth._allow_send(otp,now)[1],1)

    def test_smtp_delivery_and_failure_are_safe(self):
        with patch.object(email_sender.settings, "email_delivery_mode", "smtp"), \
             patch.object(email_sender.settings, "smtp_host", "smtp.invalid"), \
             patch.object(email_sender.settings, "smtp_username", "login"), \
             patch.object(email_sender.settings, "smtp_password", SecretStr("test-secret")), \
             patch.object(email_sender.settings, "smtp_from_email", "sender@example.com"), \
             patch("app.services.email_sender.smtplib.SMTP") as smtp:
            connection = smtp.return_value.__enter__.return_value
            email_sender.send_otp("test@example.com", "123456", "verification", 5)
            connection.starttls.assert_called_once()
            connection.login.assert_called_once()
            connection.send_message.assert_called_once()
            smtp.side_effect = TimeoutError("private transport details")
            with self.assertRaises(HTTPException) as error:
                email_sender.send_otp("test@example.com", "123456", "verification", 5)
            self.assertEqual(error.exception.status_code, 503)
            self.assertNotIn("private", error.exception.detail)


if __name__ == "__main__": unittest.main()
