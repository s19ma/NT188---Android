from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SubtitleSegmentResponse(BaseModel):
    id: int
    sequence_number: int
    start_ms: int
    end_ms: int
    content: str
    translation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SubtitleResponse(BaseModel):
    video_id: UUID
    transcript_id: UUID
    language_code: str
    format: str
    total_segments: int
    segments: List[SubtitleSegmentResponse]
