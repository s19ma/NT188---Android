from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.learning_progress import LearningProgress
from app.models.user import User
from app.models.video import Video
from app.schemas.progress import LearningProgressResponse, LearningProgressUpdate

router = APIRouter(tags=["Learning Progress"])


def _to_response(row: LearningProgress) -> LearningProgressResponse:
    title = row.video.title if row.video is not None else None
    return LearningProgressResponse(
        video_id=row.video_id,
        position_ms=row.position_ms,
        is_completed=row.is_completed,
        last_watched_at=row.last_watched_at,
        updated_at=row.updated_at,
        video_title=title,
    )


def _published_video(db: Session, video_id: UUID) -> Video:
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.status == "published",
        )
    )
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not published",
        )
    return video


@router.get(
    "/users/me/progress",
    response_model=List[LearningProgressResponse],
    summary="Danh sách tiến độ xem video của người dùng hiện tại (Protected)",
)
def list_my_progress(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(LearningProgress)
        .options(joinedload(LearningProgress.video))
        .where(LearningProgress.user_id == current_user.id)
        .order_by(LearningProgress.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.scalars(stmt).unique().all()
    return [_to_response(row) for row in rows]


@router.get(
    "/users/me/progress/{video_id}",
    response_model=LearningProgressResponse,
    summary="Tiến độ xem của một video (Protected)",
)
def get_my_video_progress(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.scalar(
        select(LearningProgress)
        .options(joinedload(LearningProgress.video))
        .where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.video_id == video_id,
        )
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning progress not found",
        )
    return _to_response(row)


@router.put(
    "/users/me/progress/{video_id}",
    response_model=LearningProgressResponse,
    summary="Lưu vị trí xem và trạng thái hoàn thành (Protected)",
)
def upsert_my_video_progress(
    video_id: UUID,
    body: LearningProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = _published_video(db, video_id)
    now = datetime.now(timezone.utc)
    row = db.scalar(
        select(LearningProgress).where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.video_id == video_id,
        )
    )
    if row is None:
        row = LearningProgress(
            user_id=current_user.id,
            video_id=video_id,
            position_ms=body.position_ms,
            is_completed=body.is_completed,
            last_watched_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.position_ms = body.position_ms
        row.is_completed = body.is_completed
        row.last_watched_at = now
        row.updated_at = now

    db.commit()
    db.refresh(row)
    row.video = video
    return _to_response(row)
