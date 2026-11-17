"""Model: users"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.learning_progress import LearningProgress
    from app.models.user_vocabulary import UserVocabulary


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "cefr_level::text = ANY (ARRAY["
            "'A1','A2','B1','B2','C1','C2']::text[])",
            name="users_cefr_level_check",
        ),
        # Functional index lower(email) — đã có sẵn trong DB, khai báo để Alembic nhận biết
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    native_language: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, server_default="vi"
    )
    target_language: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, server_default="en"
    )
    cefr_level: Mapped[Optional[str]] = mapped_column(
        String(2), nullable=True, server_default="B1"
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, server_default="true"
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    learning_progress: Mapped[List["LearningProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_vocabulary: Mapped[List["UserVocabulary"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
