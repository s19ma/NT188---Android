from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    id: str
    type: str
    prompt: str
    options: list[str] = []


class QuizResponse(BaseModel):
    id: str
    title: str
    questions: list[QuizQuestion]


class QuizSubmission(BaseModel):
    answers: dict[str, str] = Field(min_length=1)


class QuizResult(BaseModel):
    score: int
    total_questions: int
    correct_question_ids: list[str]


class QuizAttemptResponse(QuizResult):
    id: UUID
    submitted_at: datetime
