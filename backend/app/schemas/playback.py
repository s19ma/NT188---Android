from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class PlaybackResponse(BaseModel):
    video_id: UUID
    playback_url: str
    expires_at: datetime
    expires_in: int
