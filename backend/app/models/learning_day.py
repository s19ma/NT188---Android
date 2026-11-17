import uuid
from datetime import date
from sqlalchemy import Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class LearningDay(Base):
    __tablename__ = "learning_days"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
