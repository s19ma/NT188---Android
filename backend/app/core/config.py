from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "English Through Video API"
    app_environment: str = "production"
    email_delivery_mode: str = "disabled"
    email_outbox_encryption_key: SecretStr | None = None

    # Database
    database_url: str
    direct_database_url: str

    @field_validator("database_url", "direct_database_url")
    @classmethod
    def select_postgres_driver(cls, url: str) -> str:
        if url.startswith(("postgresql://", "postgres://")):
            return "postgresql+psycopg://" + url.split("://", 1)[1]
        return url

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Password reset email (SMTP). These remain optional until the feature is enabled.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "English Through Video"
    smtp_use_tls: bool = True
    password_reset_otp_expire_minutes: int = 5
    email_verification_otp_expire_minutes: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_sends_per_hour: int = 5

    # Comma-separated email addresses allowed to access /admin endpoints.
    admin_emails: str = ""

    # Azure Blob Storage
    azure_storage_account_name: str
    azure_storage_account_key: SecretStr
    azure_storage_container_videos: str = "videos"
    azure_storage_container_thumbnails: str = "thumbnails"
    azure_storage_container_subtitles: str = "subtitles"

    # SAS configuration
    azure_sas_expire_minutes: int = 30
    admin_max_video_upload_bytes: int = 536870912
    admin_max_thumbnail_upload_bytes: int = 10485760
    admin_max_subtitle_upload_bytes: int = 2097152

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
