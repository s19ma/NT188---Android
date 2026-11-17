"""Model: videos"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.learning_progress import LearningProgress
    from app.models.transcript import Transcript
    from app.models.user_vocabulary import UserVocabulary
    from app.models.video_summary import VideoSummary


class Video(Base):
    __tablename__ = "videos"

    __table_args__ = (
        CheckConstraint(
            "cefr_level::text = ANY (ARRAY["
            "'A1','A2','B1','B2','C1','C2']::text[])",
            name="videos_cefr_level_check",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="videos_duration_seconds_check",
        ),
        CheckConstraint(
            "status::text = ANY (ARRAY["
            "'draft','published','archived']::text[])",
            name="videos_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cefr_level: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blob_name: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_blob_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    transcripts: Mapped[List["Transcript"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    learning_progress: Mapped[List["LearningProgress"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    user_vocabulary_refs: Mapped[List["UserVocabulary"]] = relationship(
        back_populates="video"
    )
    summary: Mapped[Optional["VideoSummary"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id} title={self.title!r} status={self.status!r}>"
