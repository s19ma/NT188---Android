from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class DailyFlashcardGoal(Base):
    __tablename__ = 'daily_flashcard_goals'

    user_id: Mapped[object] = mapped_column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    saved_id: Mapped[object] = mapped_column(Uuid, primary_key=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
