"""Model: learning_progress (Composite PK: user_id + video_id)"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    __table_args__ = (
        CheckConstraint("position_ms >= 0", name="learning_progress_position_ms_check"),
    )

    # Composite Primary Key
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    position_ms: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    last_watched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="learning_progress")
    video: Mapped["Video"] = relationship(back_populates="learning_progress")

    def __repr__(self) -> str:
        return (
            f"<LearningProgress user={self.user_id} video={self.video_id} "
            f"pos={self.position_ms}ms completed={self.is_completed}>"
        )
