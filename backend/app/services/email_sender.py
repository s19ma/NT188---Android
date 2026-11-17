"""OTP delivery. Mock mode never sends or logs an OTP."""
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from fastapi import HTTPException
from app.core.config import settings


class DeliveryError(HTTPException):
    def __init__(self, retryable: bool):
        super().__init__(status_code=503, detail="Email service is temporarily unavailable.")
        self.retryable = retryable


def ensure_available():
    if settings.email_delivery_mode == "mock" and settings.app_environment == "development":
        return
    if settings.email_delivery_mode == "smtp" and settings.smtp_host and settings.smtp_from_email and settings.smtp_username and settings.smtp_password:
        return
    raise HTTPException(status_code=503, detail="Email delivery is not configured.")


def send_otp(email: str, code: str, purpose: str, minutes: int):
    ensure_available()
    if settings.email_delivery_mode == "mock":
        return
    message = EmailMessage()
    message["Subject"] = "English Through Video – " + purpose
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = email
    message.set_content(f"Hello,\n\nYour English Through Video verification code is: {code}\n"
                        f"This code expires in {minutes} minutes. Do not share it with anyone.\n\n"
                        "If you did not request this code, you can ignore this email.\n\nEnglish Through Video")
    sending = False
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            sending = True
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError):
        raise DeliveryError(retryable=not sending)
