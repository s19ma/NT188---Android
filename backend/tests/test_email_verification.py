import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from fastapi import HTTPException
from app.api.v1.endpoints.auth import confirm_verification, send_verification_code
from app.schemas.auth import PasswordResetVerify


class EmailVerificationTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="user-id", email="test@example.com", is_active=True, email_verified=False)
        self.otp = SimpleNamespace(code_hash="stored", attempts=0, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
        self.db = Mock()
        self.db.scalar.side_effect = [self.user, self.otp]
        self.payload = PasswordResetVerify(email=self.user.email, code="123456")

    @patch("app.api.v1.endpoints.auth.verify_password", return_value=True)
    def test_valid_code_verifies_once(self, verify):
        confirm_verification(self.payload, self.db)
        self.assertTrue(self.user.email_verified)
        self.db.delete.assert_called_once_with(self.otp)
        self.db.commit.assert_called_once()

    @patch("app.api.v1.endpoints.auth.verify_password", return_value=False)
    def test_invalid_code_counts_attempt(self, verify):
        with self.assertRaises(HTTPException): confirm_verification(self.payload, self.db)
        self.assertEqual(self.otp.attempts, 1)
        self.assertFalse(self.user.email_verified)
        self.db.commit.assert_called_once()

    def test_expired_code_is_rejected(self):
        self.otp.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        with self.assertRaises(HTTPException): confirm_verification(self.payload, self.db)
        self.db.commit.assert_not_called()

    def test_resend_cooldown(self):
        self.otp.created_at = datetime.now(timezone.utc)
        self.db.scalar.side_effect = None
        self.db.scalar.return_value = self.otp
        with self.assertRaises(HTTPException) as error: send_verification_code(self.user, self.db)
        self.assertEqual(error.exception.status_code, 429)


if __name__ == "__main__": unittest.main()
