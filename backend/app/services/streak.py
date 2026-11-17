from datetime import datetime, timedelta, timezone
from sqlalchemy.dialects.postgresql import insert
from app.models.learning_day import LearningDay

# Vietnam observes UTC+7 year-round; avoids a system timezone-data dependency.
VIETNAM = timezone(timedelta(hours=7))


def record_learning_day(db, user_id, now=None):
    day = (now or datetime.now(timezone.utc)).astimezone(VIETNAM).date()
    db.execute(insert(LearningDay).values(user_id=user_id, activity_date=day).on_conflict_do_nothing())


def streak_summary(days, today):
    days = set(days)
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    monday = today - timedelta(days=today.weekday())
    return count, [(monday + timedelta(days=i), monday + timedelta(days=i) in days) for i in range(7)]
