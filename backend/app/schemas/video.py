from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class VideoResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    cefr_level: Optional[str] = None
    category: Optional[str] = None
    duration_seconds: Optional[int] = None
    blob_name: str
    thumbnail_blob_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VideoSummaryResponse(BaseModel):
    video_id: UUID
    summary_text: Optional[str] = None
    key_points: list[str]
    source: str
    updated_at: Optional[datetime] = None


class VideoSummaryUpsertRequest(BaseModel):
    summary_text: Optional[str] = None
    key_points: list[str]
    source: Literal["manual", "ai"] = "manual"
