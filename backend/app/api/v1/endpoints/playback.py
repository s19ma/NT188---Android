from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.playback import PlaybackResponse
from app.services.azure_storage import azure_storage

router = APIRouter(prefix="/videos", tags=["Playback"])


@router.get("/{video_id}/playback", response_model=PlaybackResponse, summary="Lấy SAS URL phát video (Protected)")
def get_video_playback(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Protected API:
    Tạo Azure read-only SAS URL để phát video.
    Yêu cầu JWT hợp lệ và video đã published.
    """
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

    # Sinh SAS URL qua Azure Storage Service
    try:
        playback_url = azure_storage.generate_read_url(
            blob_name=video.blob_name,
            resource_type="video",
            expire_minutes=settings.azure_sas_expire_minutes,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate playback URL: {str(e)}",
        )

    now = datetime.now(timezone.utc)
    expires_in_seconds = settings.azure_sas_expire_minutes * 60
    expires_at = now + timedelta(seconds=expires_in_seconds)

    return PlaybackResponse(
        video_id=video.id,
        playback_url=playback_url,
        expires_at=expires_at,
        expires_in=expires_in_seconds,
    )
