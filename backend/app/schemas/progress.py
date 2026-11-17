from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LearningProgressUpdate(BaseModel):
    position_ms: int = Field(ge=0)
    is_completed: bool = False


class LearningProgressResponse(BaseModel):
    video_id: UUID
    position_ms: int
    is_completed: bool
    last_watched_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    video_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
