from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LearningStatisticsResponse(BaseModel):
    saved_words: int
    new_words: int
    learning_words: int
    learned_words: int
    due_flashcards: int
    total_reviews: int
    videos_in_progress: int
    videos_completed: int
    last_activity_at: Optional[datetime] = None
