import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.models.video import Video
from app.models.video_summary import VideoSummary
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.schemas.admin import AdminOverview, AdminVideoCreate, AdminVideoUpdate, VideoStatusUpdate
from app.schemas.video import VideoResponse, VideoSummaryResponse, VideoSummaryUpsertRequest
from app.services.azure_storage import azure_storage
from app.services.srt_parser import parse_srt

router = APIRouter(prefix="/admin", tags=["Administration"])


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    allowed = {email.strip().lower() for email in settings.admin_emails.split(",") if email.strip()}
    if current_user.email.lower() not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return current_user


def _response(video: Video) -> VideoResponse:
    return VideoResponse(
        id=video.id, title=video.title, description=video.description,
        cefr_level=video.cefr_level, category=video.category,
        duration_seconds=video.duration_seconds, blob_name=video.blob_name,
        thumbnail_blob_name=video.thumbnail_blob_name, thumbnail_url=None,
        status=video.status, created_at=video.created_at, updated_at=video.updated_at,
    )


@router.get("/overview", response_model=AdminOverview)
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video_counts = dict(db.execute(select(Video.status, func.count()).group_by(Video.status)).all())
    return AdminOverview(
        total_users=db.scalar(select(func.count()).select_from(User)) or 0,
        active_users=db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0,
        total_videos=sum(video_counts.values()), draft_videos=video_counts.get("draft", 0),
        published_videos=video_counts.get("published", 0), archived_videos=video_counts.get("archived", 0),
        quiz_attempts=db.scalar(select(func.count()).select_from(QuizAttempt)) or 0,
    )


@router.get("/videos", response_model=list[VideoResponse])
def list_all_videos(
    q: str | None = Query(default=None, max_length=255), category: str | None = None,
    cefr_level: str | None = None, video_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=100), skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), _: User = Depends(get_current_admin),
):
    stmt = select(Video)
    if q: stmt = stmt.where(Video.title.ilike(f"%{q.strip()}%"))
    if category: stmt = stmt.where(Video.category == category)
    if cefr_level: stmt = stmt.where(Video.cefr_level == cefr_level)
    if video_status: stmt = stmt.where(Video.status == video_status)
    return [_response(video) for video in db.scalars(stmt.order_by(Video.created_at.desc()).offset(skip).limit(limit)).all()]


@router.post("/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def create_video(payload: AdminVideoCreate, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video_id = uuid.uuid4()
    video = Video(id=video_id, title=payload.title.strip(), description=payload.description,
                  category=payload.category, cefr_level=payload.cefr_level, duration_seconds=payload.duration_seconds,
                  blob_name=f"pending/{video_id}.mp4", status="draft")
    db.add(video); db.commit(); db.refresh(video)
    return _response(video)


@router.patch("/videos/{video_id}", response_model=VideoResponse)
def update_video(video_id: str, payload: AdminVideoUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video = db.scalar(select(Video).where(Video.id == video_id))
    if not video: raise HTTPException(status_code=404, detail="Video not found.")
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(video, field, value)
    db.commit(); db.refresh(video)
    return _response(video)


def _require_upload(file: UploadFile, max_bytes: int, allowed_extensions: set[str], allowed_mimes: set[str]) -> tuple[str, str]:
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    if extension not in allowed_extensions or (file.content_type and file.content_type.lower() not in allowed_mimes):
        raise HTTPException(status_code=415, detail="Unsupported file type.")
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")
    return extension, file.content_type or "application/octet-stream"


def _video_or_404(db: Session, video_id: str) -> Video:
    video = db.scalar(select(Video).where(Video.id == video_id))
    if not video: raise HTTPException(status_code=404, detail="Video not found.")
    return video


@router.post("/videos/{video_id}/upload-video", response_model=VideoResponse)
def upload_video(video_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video = _video_or_404(db, video_id)
    extension, mime = _require_upload(file, settings.admin_max_video_upload_bytes, {".mp4", ".webm", ".mov"}, {"video/mp4", "video/webm", "video/quicktime"})
    blob_name = f"videos/{video.id}/{uuid.uuid4().hex}{extension}"
    try: azure_storage.upload_stream(blob_name, file.file, "video", mime)
    except Exception as error: raise HTTPException(status_code=502, detail="Video upload to storage failed.") from error
    video.blob_name = blob_name; db.commit(); db.refresh(video)
    return _response(video)


@router.post("/videos/{video_id}/upload-thumbnail", response_model=VideoResponse)
def upload_thumbnail(video_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video = _video_or_404(db, video_id)
    extension, mime = _require_upload(file, settings.admin_max_thumbnail_upload_bytes, {".jpg", ".jpeg", ".png", ".webp"}, {"image/jpeg", "image/png", "image/webp"})
    blob_name = f"thumbnails/{video.id}/{uuid.uuid4().hex}{extension}"
    try: azure_storage.upload_stream(blob_name, file.file, "thumbnail", mime)
    except Exception as error: raise HTTPException(status_code=502, detail="Thumbnail upload to storage failed.") from error
    video.thumbnail_blob_name = blob_name; db.commit(); db.refresh(video)
    return _response(video)


@router.post("/videos/{video_id}/upload-subtitle")
def upload_subtitle(video_id: str, language_code: str = Query(default="en", min_length=2, max_length=10), file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video = _video_or_404(db, video_id)
    _require_upload(file, settings.admin_max_subtitle_upload_bytes, {".srt"}, {"application/x-subrip", "text/plain", "application/octet-stream"})
    raw = file.file.read()
    if len(raw) > settings.admin_max_subtitle_upload_bytes: raise HTTPException(status_code=413, detail="Subtitle exceeds the configured upload limit.")
    try: segments = parse_srt(raw)
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    blob_name = f"subtitles/{video.id}/{language_code}/{uuid.uuid4().hex}.srt"
    try: azure_storage.upload_stream(blob_name, raw, "subtitle", "application/x-subrip")
    except Exception as error: raise HTTPException(status_code=502, detail="Subtitle upload to storage failed.") from error
    transcript = db.scalar(select(Transcript).where(Transcript.video_id == video.id, Transcript.language_code == language_code))
    if not transcript:
        transcript = Transcript(video_id=video.id, language_code=language_code, format="srt", is_default=True); db.add(transcript); db.flush()
    db.execute(delete(TranscriptSegment).where(TranscriptSegment.transcript_id == transcript.id))
    transcript.blob_name = blob_name
    for item in segments: db.add(TranscriptSegment(transcript_id=transcript.id, **item))
    db.commit()
    return {"video_id": str(video.id), "language_code": language_code, "segments": len(segments), "blob_name": blob_name}


@router.post("/videos/{video_id}/publish", response_model=VideoResponse)
def publish_video(video_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video = _video_or_404(db, video_id)
    missing = []
    if video.blob_name.startswith("pending/") or not azure_storage.blob_exists(video.blob_name, "video"): missing.append("video")
    if not video.thumbnail_blob_name or not azure_storage.blob_exists(video.thumbnail_blob_name, "thumbnail"): missing.append("thumbnail")
    if not db.scalar(select(Transcript.id).where(Transcript.video_id == video.id)): missing.append("subtitle")
    if missing: raise HTTPException(status_code=422, detail={"message": "Cannot publish until required assets are ready.", "missing": missing})
    video.status = "published"; db.commit(); db.refresh(video)
    return _response(video)


@router.patch("/videos/{video_id}/status", response_model=VideoResponse)
def update_video_status(video_id: str, payload: VideoStatusUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    video = db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    video.status = payload.status
    db.commit()
    db.refresh(video)
    return _response(video)


@router.put("/videos/{video_id}/summary", response_model=VideoSummaryResponse)
def upsert_video_summary(
    video_id: str,
    payload: VideoSummaryUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    video = db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    if not payload.key_points:
        raise HTTPException(status_code=422, detail="At least one key point is required.")
    summary = db.scalar(select(VideoSummary).where(VideoSummary.video_id == video.id))
    if not summary:
        summary = VideoSummary(video_id=video.id)
        db.add(summary)
    summary.summary_text = payload.summary_text
    summary.key_points = payload.key_points
    summary.source = payload.source
    db.commit()
    db.refresh(summary)
    return VideoSummaryResponse(video_id=video.id, summary_text=summary.summary_text,
        key_points=summary.key_points, source=summary.source, updated_at=summary.updated_at)
