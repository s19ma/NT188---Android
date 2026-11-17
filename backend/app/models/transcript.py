"""Model: transcripts"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.transcript_segment import TranscriptSegment
    from app.models.video import Video


class Transcript(Base):
    __tablename__ = "transcripts"

    __table_args__ = (
        UniqueConstraint(
            "video_id", "language_code",
            name="transcripts_video_id_language_code_key",
        ),
        CheckConstraint(
            "format::text = ANY (ARRAY['srt','vtt']::text[])",
            name="transcripts_format_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_code: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="en"
    )
    format: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="srt"
    )
    blob_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, server_default="false"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    video: Mapped["Video"] = relationship(back_populates="transcripts")
    segments: Mapped[List["TranscriptSegment"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transcript id={self.id} video_id={self.video_id} lang={self.language_code!r}>"
