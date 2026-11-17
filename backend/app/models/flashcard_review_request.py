"""Committed results for safely replaying a flashcard review request."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class FlashcardReviewRequest(Base):
    __tablename__ = "flashcard_review_requests"
    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    request_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    saved_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("user_vocabulary.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
