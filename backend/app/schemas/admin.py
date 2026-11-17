from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AdminOverview(BaseModel):
    total_users: int
    active_users: int
    total_videos: int
    draft_videos: int
    published_videos: int
    archived_videos: int
    quiz_attempts: int


class VideoStatusUpdate(BaseModel):
    status: Literal["draft", "published", "archived"]


class AdminVideoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=100)
    cefr_level: Optional[Literal["A1", "A2", "B1", "B2", "C1", "C2"]] = None
    duration_seconds: Optional[int] = Field(default=None, ge=0)


class AdminVideoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=100)
    cefr_level: Optional[Literal["A1", "A2", "B1", "B2", "C1", "C2"]] = None
    duration_seconds: Optional[int] = Field(default=None, ge=0)


class AdminVideoListResponse(BaseModel):
    items: list
    total: int
    limit: int
    skip: int
