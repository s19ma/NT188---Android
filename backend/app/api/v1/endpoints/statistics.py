from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.learning_progress import LearningProgress
from app.models.user import User
from app.models.user_vocabulary import UserVocabulary
from app.schemas.statistics import LearningStatisticsResponse
from app.models.learning_day import LearningDay
from app.services.streak import VIETNAM, streak_summary

router = APIRouter(tags=["Statistics"])


@router.get("/users/me/streak")
def get_my_streak(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = datetime.now(VIETNAM).date()
    days = db.scalars(select(LearningDay.activity_date).where(
        LearningDay.user_id == current_user.id, LearningDay.activity_date <= today)).all()
    count, week = streak_summary(days, today)
    return {"current_streak": count, "today": today.isoformat(), "week": [
        {"date": day.isoformat(), "active": active} for day, active in week]}


@router.get(
    "/users/me/statistics",
    response_model=LearningStatisticsResponse,
    summary="Thống kê tiến độ học của người dùng hiện tại (Protected)",
)
def get_my_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status_rows = db.execute(
        select(UserVocabulary.learning_status, func.count())
        .where(UserVocabulary.user_id == current_user.id)
        .group_by(UserVocabulary.learning_status)
    ).all()
    counts = {status: count for status, count in status_rows}

    due_flashcards = db.scalar(
        select(func.count())
        .select_from(UserVocabulary)
        .where(
            UserVocabulary.user_id == current_user.id,
            or_(
                UserVocabulary.next_review_at.is_(None),
                UserVocabulary.next_review_at <= func.now(),
            ),
        )
    ) or 0

    total_reviews = db.scalar(
        select(func.coalesce(func.sum(UserVocabulary.review_count), 0)).where(
            UserVocabulary.user_id == current_user.id
        )
    ) or 0

    videos_completed = db.scalar(
        select(func.count())
        .select_from(LearningProgress)
        .where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.is_completed.is_(True),
        )
    ) or 0

    videos_in_progress = db.scalar(
        select(func.count())
        .select_from(LearningProgress)
        .where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.is_completed.is_(False),
        )
    ) or 0

    last_saved = db.scalar(
        select(func.max(UserVocabulary.saved_at)).where(
            UserVocabulary.user_id == current_user.id
        )
    )
    last_reviewed = db.scalar(
        select(func.max(UserVocabulary.last_reviewed_at)).where(
            UserVocabulary.user_id == current_user.id
        )
    )
    last_watched = db.scalar(
        select(func.max(LearningProgress.last_watched_at)).where(
            LearningProgress.user_id == current_user.id
        )
    )
    activity = [value for value in (last_saved, last_reviewed, last_watched) if value]
    last_activity_at = max(activity) if activity else None

    new_words = int(counts.get("new", 0))
    learning_words = int(counts.get("learning", 0))
    learned_words = int(counts.get("learned", 0))

    return LearningStatisticsResponse(
        saved_words=new_words + learning_words + learned_words,
        new_words=new_words,
        learning_words=learning_words,
        learned_words=learned_words,
        due_flashcards=int(due_flashcards),
        total_reviews=int(total_reviews),
        videos_in_progress=int(videos_in_progress),
        videos_completed=int(videos_completed),
        last_activity_at=last_activity_at,
    )
