"""Model: vocabulary"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user_vocabulary import UserVocabulary


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    __table_args__ = (
        UniqueConstraint(
            "language_code", "lemma",
            name="vocabulary_language_code_lemma_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    lemma: Mapped[str] = mapped_column(String(150), nullable=False)
    language_code: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="en"
    )
    phonetic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vietnamese_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    user_vocabulary: Mapped[List["UserVocabulary"]] = relationship(
        back_populates="vocabulary", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vocabulary id={self.id} lemma={self.lemma!r} lang={self.language_code!r}>"
