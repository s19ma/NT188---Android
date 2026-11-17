"""Model: transcript_segments
id là BIGINT GENERATED ALWAYS AS IDENTITY (PostgreSQL identity column).
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.transcript import Transcript
    from app.models.user_vocabulary import UserVocabulary


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    __table_args__ = (
        UniqueConstraint(
            "transcript_id", "sequence_number",
            name="transcript_segments_transcript_id_sequence_number_key",
        ),
        CheckConstraint("start_ms >= 0", name="transcript_segments_start_ms_check"),
        CheckConstraint("end_ms > start_ms",   name="transcript_segments_check"),
        # Index tăng tốc tìm segment theo timestamp
        Index("idx_segments_transcript_start", "transcript_id", "start_ms"),
    )

    # BIGINT GENERATED ALWAYS AS IDENTITY — không dùng UUID
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    transcript_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    translation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    transcript: Mapped["Transcript"] = relationship(back_populates="segments")
    user_vocabulary_refs: Mapped[List["UserVocabulary"]] = relationship(
        back_populates="transcript_segment"
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptSegment id={self.id} seq={self.sequence_number} "
            f"{self.start_ms}-{self.end_ms}ms>"
        )
