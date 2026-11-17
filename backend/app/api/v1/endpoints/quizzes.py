from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.schemas.quiz import QuizAttemptResponse, QuizResponse, QuizResult, QuizSubmission

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

DEFAULT_QUIZ = {
    "id": "everyday-english-1",
    "title": "Everyday English",
    "questions": [
        {"id": "q1", "type": "multiple_choice", "prompt": "Choose the correct sentence.",
         "options": ["She go to school.", "She goes to school.", "She going to school."]},
        {"id": "q2", "type": "fill_blank", "prompt": "I ___ English videos every day.", "options": []},
        {"id": "q3", "type": "dictation", "prompt": "Type exactly: Practice makes progress.", "options": []},
    ],
}
ANSWERS = {"q1": "She goes to school.", "q2": "watch", "q3": "practice makes progress"}


@router.get("/default", response_model=QuizResponse)
def get_default_quiz(current_user: User = Depends(get_current_user)):
    return DEFAULT_QUIZ


@router.post("/default/submit", response_model=QuizResult)
def submit_default_quiz(
    payload: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    correct = [
        question_id for question_id, answer in ANSWERS.items()
        if payload.answers.get(question_id, "").strip().casefold() == answer.casefold()
    ]
    attempt = QuizAttempt(
        user_id=current_user.id,
        score=len(correct),
        total_questions=len(ANSWERS),
    )
    db.add(attempt)
    db.commit()
    return QuizResult(
        score=attempt.score,
        total_questions=attempt.total_questions,
        correct_question_ids=correct,
    )


@router.get("/history", response_model=list[QuizAttemptResponse])
def quiz_history(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    attempts = db.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.submitted_at.desc())
        .limit(20)
    ).all()
    return [
        QuizAttemptResponse(
            id=attempt.id,
            score=attempt.score,
            total_questions=attempt.total_questions,
            correct_question_ids=[],
            submitted_at=attempt.submitted_at,
        )
        for attempt in attempts
    ]
