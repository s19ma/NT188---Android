from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.video import Video
from app.models.video_summary import VideoSummary
from app.schemas.video import VideoResponse, VideoSummaryResponse
from app.services.azure_storage import azure_storage

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.get("", response_model=List[VideoResponse], summary="Lấy danh sách video đã published (Public)")
def list_published_videos(
    cefr_level: Optional[str] = Query(None, description="Lọc theo trình độ CEFR (A1-C2)"),
    category: Optional[str] = Query(None, description="Lọc theo danh mục"),
    db: Session = Depends(get_db),
):
    stmt = select(Video).where(Video.status == "published").order_by(Video.created_at.desc())

    if cefr_level:
        stmt = stmt.where(Video.cefr_level == cefr_level)
    if category:
        stmt = stmt.where(Video.category == category)

    videos = db.scalars(stmt).all()

    result = []
    for v in videos:
        v_dict = {
            "id": v.id,
            "title": v.title,
            "description": v.description,
            "cefr_level": v.cefr_level,
            "category": v.category,
            "duration_seconds": v.duration_seconds,
            "blob_name": v.blob_name,
            "thumbnail_blob_name": v.thumbnail_blob_name,
            "thumbnail_url": None,
            "status": v.status,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
        }
        if v.thumbnail_blob_name:
            try:
                v_dict["thumbnail_url"] = azure_storage.generate_read_url(
                    v.thumbnail_blob_name, resource_type="thumbnail"
                )
            except Exception:
                pass
        result.append(VideoResponse(**v_dict))

    return result


@router.get("/{video_id}", response_model=VideoResponse, summary="Lấy chi tiết video đã published (Public)")
def get_published_video_detail(
    video_id: UUID,
    db: Session = Depends(get_db),
):
    stmt = select(Video).where(Video.id == video_id, Video.status == "published")
    video = db.scalar(stmt)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not published",
        )

    v_dict = {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "cefr_level": video.cefr_level,
        "category": video.category,
        "duration_seconds": video.duration_seconds,
        "blob_name": video.blob_name,
        "thumbnail_blob_name": video.thumbnail_blob_name,
        "thumbnail_url": None,
        "status": video.status,
        "created_at": video.created_at,
        "updated_at": video.updated_at,
    }
    if video.thumbnail_blob_name:
        try:
            v_dict["thumbnail_url"] = azure_storage.generate_read_url(
                video.thumbnail_blob_name, resource_type="thumbnail"
            )
        except Exception:
            pass

    return VideoResponse(**v_dict)


@router.get("/{video_id}/summary", response_model=VideoSummaryResponse, summary="Lấy tóm tắt học tập của video")
def get_published_video_summary(video_id: UUID, db: Session = Depends(get_db)):
    video = db.scalar(select(Video).where(Video.id == video_id, Video.status == "published"))
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found or not published")
    summary = db.scalar(select(VideoSummary).where(VideoSummary.video_id == video.id))
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video summary has not been created yet.")
    return VideoSummaryResponse(
        video_id=video.id, summary_text=summary.summary_text, key_points=summary.key_points,
        source=summary.source, updated_at=summary.updated_at,
    )
