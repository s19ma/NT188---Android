from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.models.video import Video
from app.schemas.subtitle import SubtitleResponse, SubtitleSegmentResponse

router = APIRouter(prefix="/videos", tags=["Subtitles"])


@router.get("/{video_id}/subtitles", response_model=SubtitleResponse, summary="Lấy danh sách subtitle segments từ PostgreSQL (Protected)")
def get_video_subtitles(
    video_id: UUID,
    language_code: str = Query(default="en", min_length=2, max_length=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Protected API:
    Lấy transcript và các subtitle segments từ Neon PostgreSQL.
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

    # Tìm transcript của video theo language_code
    stmt_transcript = select(Transcript).where(
        Transcript.video_id == video.id,
        Transcript.language_code == language_code,
    )
    transcript = db.scalar(stmt_transcript)

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript not found for language '{language_code}'",
        )

    # Lấy toàn bộ segments sắp xếp theo sequence_number
    stmt_segments = (
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == transcript.id)
        .order_by(TranscriptSegment.sequence_number.asc())
    )
    segments = db.scalars(stmt_segments).all()

    return SubtitleResponse(
        video_id=video.id,
        transcript_id=transcript.id,
        language_code=transcript.language_code,
        format=transcript.format,
        total_segments=len(segments),
        segments=[SubtitleSegmentResponse.model_validate(s) for s in segments],
    )
