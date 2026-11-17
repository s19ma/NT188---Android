from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class VocabularyResponse(BaseModel):
    id: UUID
    lemma: str
    language_code: str
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    definition: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DictionaryLookupResponse(BaseModel):
    vocabulary_id: UUID
    word: str
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    english_definition: Optional[str] = None
    example: Optional[str] = None
    audio_url: Optional[str] = None
    synonyms: list[str] = []
    antonyms: list[str] = []
    provider: str


class SaveVocabularyRequest(BaseModel):
    video_id: Optional[UUID] = None
    transcript_segment_id: Optional[int] = None
    context_sentence: Optional[str] = Field(default=None, max_length=5000)


class UserVocabularyResponse(BaseModel):
    id: UUID
    vocabulary_id: UUID
    video_id: Optional[UUID] = None
    transcript_segment_id: Optional[int] = None
    context_sentence: Optional[str] = None
    saved_at: Optional[datetime] = None
    learning_status: str = "new"
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    review_count: int = 0
    next_review_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    vocabulary: VocabularyResponse

    model_config = ConfigDict(from_attributes=True)


class UpdateLearningStatusRequest(BaseModel):
    learning_status: Literal["new", "learning", "learned"]


class ReviewVocabularyRequest(BaseModel):
    rating: Literal["again", "hard", "good", "easy"]
    request_id: Optional[UUID] = None


class FlashcardOverviewResponse(BaseModel):
    due: int
    new: int
    learning: int
    learned: int
    idempotent_review_supported: bool = True
    daily_goal_total: int = 0
    daily_goal_remaining: int = 0
    fixed_review_intervals: bool = True
