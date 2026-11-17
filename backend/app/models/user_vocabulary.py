"""Model: user_vocabulary"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.transcript_segment import TranscriptSegment
    from app.models.user import User
    from app.models.video import Video
    from app.models.vocabulary import Vocabulary


class UserVocabulary(Base):
    __tablename__ = "user_vocabulary"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "vocabulary_id",
            name="user_vocabulary_user_id_vocabulary_id_key",
        ),
        CheckConstraint(
            "learning_status::text = ANY (ARRAY["
            "'new','learning','learned']::text[])",
            name="user_vocabulary_learning_status_check",
        ),
        CheckConstraint(
            "ease_factor >= 1.3",
            name="user_vocabulary_ease_factor_check",
        ),
        CheckConstraint(
            "interval_days >= 0",
            name="user_vocabulary_interval_days_check",
        ),
        CheckConstraint(
            "repetitions >= 0",
            name="user_vocabulary_repetitions_check",
        ),
        CheckConstraint(
            "review_count >= 0",
            name="user_vocabulary_review_count_check",
        ),
        Index("idx_user_vocabulary_user", "user_id"),
        Index("idx_user_vocabulary_user_review", "user_id", "next_review_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vocabulary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vocabulary.id", ondelete="CASCADE"),
        nullable=False,
    )
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
    )
    transcript_segment_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("transcript_segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_sentence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    saved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    # new = vừa lưu; learning = đang học; learned = ít nhất 4 lần đúng liên tiếp hoặc gán thủ công.
    learning_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="new", default="new"
    )
    ease_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        server_default="2.50",
        default=Decimal("2.50"),
    )
    interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    repetitions: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    review_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    next_review_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="saved_vocabulary")
    vocabulary: Mapped["Vocabulary"] = relationship(back_populates="user_vocabulary")
    video: Mapped[Optional["Video"]] = relationship(back_populates="user_vocabulary_refs")
    transcript_segment: Mapped[Optional["TranscriptSegment"]] = relationship(
        back_populates="user_vocabulary_refs"
    )

    def __repr__(self) -> str:
        return f"<UserVocabulary id={self.id} user={self.user_id} vocab={self.vocabulary_id}>"
