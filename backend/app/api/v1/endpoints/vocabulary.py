import logging
import re
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.models.user_vocabulary import UserVocabulary
from app.models.daily_flashcard_goal import DailyFlashcardGoal
from app.models.video import Video
from app.models.vocabulary import Vocabulary
from app.schemas.vocabulary import (
    ReviewVocabularyRequest,
    FlashcardOverviewResponse,
    DictionaryLookupResponse,
    SaveVocabularyRequest,
    UpdateLearningStatusRequest,
    UserVocabularyResponse,
    VocabularyResponse,
)

from app.services.review_scheduler import apply_learning_status, apply_rating
from app.services.streak import VIETNAM, record_learning_day

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Vocabulary"])
flashcard_router = APIRouter(tags=["Flashcards"])


# --------------------------------------------------
# PUBLIC: 1. LIST VOCABULARY
# --------------------------------------------------
@router.get(
    "/vocabulary",
    response_model=List[VocabularyResponse],
    summary="Danh sách từ vựng từ điển (Public)",
)
def get_vocabulary_list(
    language_code: str = Query(default="en", min_length=2, max_length=10),
    part_of_speech: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Vocabulary)
        .where(Vocabulary.language_code == language_code)
        .order_by(Vocabulary.lemma.asc())
        .offset(skip)
        .limit(limit)
    )
    if part_of_speech:
        stmt = stmt.where(Vocabulary.part_of_speech == part_of_speech)

    return db.scalars(stmt).all()


# --------------------------------------------------
# PUBLIC: 2. SEARCH VOCABULARY
# --------------------------------------------------
@router.get(
    "/vocabulary/search",
    response_model=List[VocabularyResponse],
    summary="Tìm kiếm từ vựng theo từ khóa hoặc định nghĩa (Public)",
)
def search_vocabulary(
    q: str = Query(..., min_length=1, max_length=100, description="Từ khóa tìm kiếm"),
    language_code: str = Query(default="en", min_length=2, max_length=10),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    keyword = f"%{q.strip().lower()}%"
    stmt = (
        select(Vocabulary)
        .where(
            Vocabulary.language_code == language_code,
            or_(
                func.lower(Vocabulary.lemma).like(keyword),
                func.lower(Vocabulary.definition).like(keyword),
            ),
        )
        .order_by(Vocabulary.lemma.asc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.get("/dictionary/{word}", response_model=DictionaryLookupResponse,
            summary="Tra từ qua Dictionary API và cache vào Vocabulary")
def dictionary_lookup(word: str, db: Session = Depends(get_db)):
    normalized = word.strip().lower()
    if not re.fullmatch(r"[a-z][a-z'-]{0,99}", normalized):
        raise HTTPException(status_code=422, detail="Word must contain English letters only")
    cached = db.scalar(select(Vocabulary).where(
        Vocabulary.language_code == "en", func.lower(Vocabulary.lemma) == normalized
    ))
    if cached:
        return DictionaryLookupResponse(
            vocabulary_id=cached.id, word=cached.lemma, phonetic=cached.phonetic,
            part_of_speech=cached.part_of_speech, english_definition=cached.definition,
            provider="postgresql-cache",
        )
    request = Request(
        f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(normalized)}",
        headers={"Accept": "application/json", "User-Agent": "EnglishThroughVideo/1.0"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            raise HTTPException(status_code=404, detail="Word not found in dictionary")
        raise HTTPException(status_code=502, detail="Dictionary provider is unavailable")
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Dictionary provider could not be reached")
    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=502, detail="Dictionary provider returned an invalid response")
    entry = payload[0]
    meanings = entry.get("meanings") or []
    meaning = meanings[0] if meanings else {}
    definitions = meaning.get("definitions") or []
    definition = definitions[0] if definitions else {}
    phonetics = entry.get("phonetics") or []
    phonetic = entry.get("phonetic") or next((p.get("text") for p in phonetics if p.get("text")), None)
    audio = next((p.get("audio") for p in phonetics if p.get("audio")), None)
    if audio and audio.startswith("//"):
        audio = "https:" + audio
    cached = Vocabulary(
        lemma=entry.get("word", normalized).lower(), language_code="en", phonetic=phonetic,
        part_of_speech=meaning.get("partOfSpeech"), definition=definition.get("definition"),
    )
    db.add(cached)
    try:
        db.commit()
        db.refresh(cached)
    except IntegrityError:
        db.rollback()
        cached = db.scalar(select(Vocabulary).where(
            Vocabulary.language_code == "en", func.lower(Vocabulary.lemma) == normalized
        ))
    return DictionaryLookupResponse(
        vocabulary_id=cached.id, word=cached.lemma, phonetic=phonetic,
        part_of_speech=meaning.get("partOfSpeech"), english_definition=definition.get("definition"),
        example=definition.get("example"), audio_url=audio,
        synonyms=definition.get("synonyms") or meaning.get("synonyms") or [],
        antonyms=definition.get("antonyms") or meaning.get("antonyms") or [],
        provider="dictionaryapi.dev",
    )


@router.get(
    "/videos/{video_id}/vocabulary",
    response_model=List[VocabularyResponse],
    summary="Từ vựng có trong transcript của một video (Protected)",
)
def get_video_vocabulary(
    video_id: UUID,
    limit: int = Query(default=30, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.scalar(select(Video).where(Video.id == video_id, Video.status == "published"))
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found or not published")
    lines = db.scalars(
        select(TranscriptSegment.content)
        .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
        .where(Transcript.video_id == video_id)
    ).all()
    transcript_words = set(re.findall(r"[a-z]+", " ".join(lines).lower()))
    if not transcript_words:
        return []
    return db.scalars(
        select(Vocabulary)
        .where(Vocabulary.language_code == "en", func.lower(Vocabulary.lemma).in_(transcript_words))
        .order_by(Vocabulary.lemma.asc())
        .limit(limit)
    ).all()


# --------------------------------------------------
# PUBLIC: 3. DETAIL VOCABULARY
# --------------------------------------------------
@router.get(
    "/vocabulary/{vocabulary_id}",
    response_model=VocabularyResponse,
    summary="Chi tiết từ vựng theo ID (Public)",
)
def get_vocabulary_detail(
    vocabulary_id: UUID,
    db: Session = Depends(get_db),
):
    vocab = db.get(Vocabulary, vocabulary_id)
    if not vocab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary not found",
        )
    return vocab


# --------------------------------------------------
# PROTECTED: 4. SAVE VOCABULARY TO USER'S LIST
# --------------------------------------------------
@router.post(
    "/vocabulary/{vocabulary_id}/save",
    response_model=UserVocabularyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lưu từ vựng vào danh sách cá nhân (Protected)",
)

def save_vocabulary_for_user(
    vocabulary_id: UUID,
    body: SaveVocabularyRequest = Body(default_factory=SaveVocabularyRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lưu từ vựng vào danh sách cá nhân của người dùng.

    Protected endpoint.
    """

    # --------------------------------------------------
    # 0. Kiểm tra database backend đang kết nối
    # --------------------------------------------------
    try:
        db_info = db.execute(
            text("""
                SELECT
                    current_database() AS database_name,
                    current_schema() AS schema_name,
                    current_user AS database_user,
                    inet_server_addr() AS server_address
            """)
        ).mappings().one()

        logger.info(
            "BACKEND DATABASE INFO: %s",
            dict(db_info)
        )

    except Exception:
        logger.exception("Cannot retrieve backend database information")
        raise

    # --------------------------------------------------
    # 1. Kiểm tra vocabulary có tồn tại không
    # --------------------------------------------------
    vocab = db.get(Vocabulary, vocabulary_id)

    if not vocab:
        logger.warning(
            "VOCABULARY NOT FOUND | vocabulary_id=%s",
            vocabulary_id
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary not found",
        )

    # --------------------------------------------------
    # 2. Kiểm tra người dùng đã lưu từ này chưa
    # --------------------------------------------------
    existing_check = db.scalar(
        select(UserVocabulary).where(
            UserVocabulary.user_id == current_user.id,
            UserVocabulary.vocabulary_id == vocabulary_id,
        )
    )

    logger.info(
        "SAVE VOCAB CHECK | user_id=%s | vocabulary_id=%s | existing=%s",
        current_user.id,
        vocabulary_id,
        existing_check is not None,
    )

    if existing_check:
        logger.warning(
            "VOCABULARY ALREADY SAVED | user_id=%s | vocabulary_id=%s | saved_id=%s",
            current_user.id,
            vocabulary_id,
            existing_check.id,
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vocabulary already saved by this user",
        )

    # --------------------------------------------------
    # 3. Kiểm tra transcript segment và video
    # --------------------------------------------------
    if (
        body.transcript_segment_id is not None
        and body.video_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_id is required when transcript_segment_id is provided",
        )

    if body.video_id:

        video = db.scalar(
            select(Video).where(
                Video.id == body.video_id,
                Video.status == "published",
            )
        )

        if not video:
            logger.warning(
                "VIDEO NOT FOUND OR NOT PUBLISHED | video_id=%s",
                body.video_id,
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced video not found or not published",
            )

        if body.transcript_segment_id is not None:

            segment = db.scalar(
                select(TranscriptSegment)
                .join(
                    Transcript,
                    Transcript.id == TranscriptSegment.transcript_id
                )
                .where(
                    TranscriptSegment.id == body.transcript_segment_id,
                    Transcript.video_id == body.video_id,
                )
            )

            if not segment:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Transcript segment does not exist "
                        "or does not belong to the specified video"
                    ),
                )

    # --------------------------------------------------
    # 4. Tạo bản ghi UserVocabulary
    # --------------------------------------------------
    now = datetime.now(timezone.utc)

    user_vocab = UserVocabulary(
        user_id=current_user.id,
        vocabulary_id=vocabulary_id,
        video_id=body.video_id,
        transcript_segment_id=body.transcript_segment_id,
        context_sentence=body.context_sentence,
        learning_status="new",
        next_review_at=now,
    )

    # --------------------------------------------------
    # 5. Lưu vào database
    # --------------------------------------------------
    try:
        db.add(user_vocab)

        db.commit()

        db.refresh(user_vocab)

        logger.info(
            "SAVE VOCAB SUCCESS | user_id=%s | vocabulary_id=%s | saved_id=%s",
            current_user.id,
            vocabulary_id,
            user_vocab.id,
        )

    except IntegrityError as exc:
        db.rollback()

        # Lấy thông tin lỗi PostgreSQL thực tế
        original_error = exc.orig

        sqlstate = getattr(original_error, "sqlstate", None)

        # Một số driver PostgreSQL sử dụng thuộc tính pgcode
        if sqlstate is None:
            sqlstate = getattr(original_error, "pgcode", None)

        constraint_name = getattr(
            getattr(original_error, "diag", None),
            "constraint_name",
            None,
        )

        logger.exception(
            (
                "SAVE VOCAB INTEGRITY ERROR | "
                "user_id=%s | vocabulary_id=%s | "
                "sqlstate=%s | constraint=%s | error=%s"
            ),
            current_user.id,
            vocabulary_id,
            sqlstate,
            constraint_name,
            str(original_error),
        )

        # Chỉ lỗi unique constraint mới được xem là duplicate
        if sqlstate == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vocabulary already saved by this user",
            )

        # Các lỗi integrity khác không được đánh đồng với duplicate
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database integrity error. Check backend logs.",
        )

    # --------------------------------------------------
    # 6. Load relationship vocabulary để trả response
    # --------------------------------------------------
    result = db.scalar(
        select(UserVocabulary)
        .options(joinedload(UserVocabulary.vocabulary))
        .where(UserVocabulary.id == user_vocab.id)
    )

    return result


# --------------------------------------------------
# PROTECTED: 5. GET USER'S SAVED VOCABULARY LIST
# --------------------------------------------------
@router.get(
    "/users/me/vocabulary",
    response_model=List[UserVocabularyResponse],
    summary="Lấy danh sách từ vựng đã lưu của người dùng hiện tại (Protected)",
)
def get_user_saved_vocabulary(
    learning_status: Optional[Literal["new", "learning", "learned"]] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = [UserVocabulary.user_id == current_user.id]
    if learning_status:
        filters.append(UserVocabulary.learning_status == learning_status)
    stmt = (
        select(UserVocabulary)
        .options(joinedload(UserVocabulary.vocabulary))
        .where(*filters)
        .order_by(UserVocabulary.saved_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).unique().all()


# --------------------------------------------------
# PROTECTED: 6. DELETE SAVED VOCABULARY
# --------------------------------------------------
@router.delete(
    "/users/me/vocabulary/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa từ vựng khỏi danh sách đã lưu (Protected)",
)
def delete_user_saved_vocabulary(
    saved_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.execute(select(User.id).where(User.id == current_user.id).with_for_update())
    user_vocab = db.scalar(
        select(UserVocabulary).where(
            UserVocabulary.id == saved_id,
            UserVocabulary.user_id == current_user.id,
        )
    )
    if not user_vocab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved vocabulary entry not found or does not belong to you",
        )

    pending_goal = db.get(DailyFlashcardGoal, (current_user.id, datetime.now(VIETNAM).date(), saved_id))
    if pending_goal is not None and not pending_goal.completed:
        raise HTTPException(status_code=409, detail="Complete today's flashcard before deleting it")
    db.delete(user_vocab)
    db.commit()
    return None


def _owned_saved_word(
    db: Session,
    current_user: User,
    saved_id: UUID,
) -> UserVocabulary:
    user_vocab = db.scalar(
        select(UserVocabulary)
        .options(joinedload(UserVocabulary.vocabulary))
        .where(
            UserVocabulary.id == saved_id,
            UserVocabulary.user_id == current_user.id,
        )
    )
    if not user_vocab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved vocabulary entry not found or does not belong to you",
        )
    return user_vocab


# --------------------------------------------------
# PROTECTED: 7. UPDATE LEARNING STATUS
# --------------------------------------------------
@router.patch(
    "/users/me/vocabulary/{saved_id}/status",
    response_model=UserVocabularyResponse,
    summary="Cập nhật trạng thái đã học / đang học / chưa học (Protected)",
)
def update_saved_vocabulary_status(
    saved_id: UUID,
    body: UpdateLearningStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_vocab = _owned_saved_word(db, current_user, saved_id)
    apply_learning_status(user_vocab, body.learning_status, datetime.now(timezone.utc))
    db.commit()
    db.refresh(user_vocab)
    return user_vocab


# --------------------------------------------------
# PROTECTED: FLASHCARDS
# --------------------------------------------------
@flashcard_router.get(
    "/users/me/flashcards/overview",
    response_model=FlashcardOverviewResponse,
    summary="Tổng quan thẻ ôn theo người dùng (Protected)",
)
def get_flashcard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status_counts = dict(
        db.execute(
            select(UserVocabulary.learning_status, func.count())
            .where(UserVocabulary.user_id == current_user.id)
            .group_by(UserVocabulary.learning_status)
        ).all()
    )
    today = datetime.now(VIETNAM).date()
    goals = db.scalars(select(DailyFlashcardGoal).where(
        DailyFlashcardGoal.user_id == current_user.id, DailyFlashcardGoal.activity_date == today)).all()
    remaining = [g.saved_id for g in goals if not g.completed]
    due_filters = [UserVocabulary.user_id == current_user.id,
                   or_(UserVocabulary.next_review_at.is_(None), UserVocabulary.next_review_at <= func.now())]
    if goals:
        due_filters.append(UserVocabulary.id.in_(remaining))
    due = db.scalar(
        select(func.count())
        .select_from(UserVocabulary)
        .where(*due_filters)
    )
    return FlashcardOverviewResponse(
        due=min(int(due or 0), 30),
        new=int(status_counts.get("new", 0)),
        learning=int(status_counts.get("learning", 0)),
        learned=int(status_counts.get("learned", 0)),
        daily_goal_total=len(goals) if goals else min(int(due or 0), 30),
        daily_goal_remaining=len(remaining) if goals else min(int(due or 0), 30),
    )


@flashcard_router.get(
    "/users/me/flashcards",
    response_model=List[UserVocabularyResponse],
    summary="Lấy thẻ ôn từ vựng đến hạn (Protected)",
)
def get_due_flashcards(
    due_only: bool = Query(default=True),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = [UserVocabulary.user_id == current_user.id]
    if due_only:
        today = datetime.now(VIETNAM).date()
        goals = db.scalars(select(DailyFlashcardGoal).where(
            DailyFlashcardGoal.user_id == current_user.id, DailyFlashcardGoal.activity_date == today)).all()
        if goals:
            filters.append(UserVocabulary.id.in_([g.saved_id for g in goals if not g.completed]))
        filters.append(
            or_(
                UserVocabulary.next_review_at.is_(None),
                UserVocabulary.next_review_at <= func.now(),
            )
        )
    stmt = (
        select(UserVocabulary)
        .options(joinedload(UserVocabulary.vocabulary))
        .where(*filters)
        .order_by(
            UserVocabulary.next_review_at.asc().nullsfirst(),
            UserVocabulary.id.asc(),
        )
        .limit(min(limit, 30) if due_only else limit)
    )
    return db.scalars(stmt).unique().all()


@flashcard_router.post(
    "/users/me/flashcards/{saved_id}/review",
    response_model=UserVocabularyResponse,
    summary="Ghi nhận kết quả ôn tập và lập lịch ôn tiếp theo (Protected)",
)
def review_flashcard(
    saved_id: UUID,
    body: ReviewVocabularyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.flashcard_review_request import FlashcardReviewRequest
    if body.request_id is not None:
        # Serialize identical keys even when simultaneous requests target different cards.
        db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(
            str(current_user.id) + ":" + str(body.request_id), 0))))
        prior = db.get(FlashcardReviewRequest, (current_user.id, body.request_id))
        if prior is not None:
            if prior.saved_id != saved_id or prior.rating != body.rating:
                raise HTTPException(status_code=409, detail="Review request ID already used for another action")
            if db.scalar(select(UserVocabulary.id).where(UserVocabulary.id == saved_id,
                                                         UserVocabulary.user_id == current_user.id)) is None:
                raise HTTPException(status_code=404, detail="Saved vocabulary entry not found")
            return prior.response
    # Serialize all reviews for this user so the daily set cannot exceed 30 under concurrency.
    db.execute(select(User.id).where(User.id == current_user.id).with_for_update())
    user_vocab = db.scalar(select(UserVocabulary).where(
        UserVocabulary.id == saved_id, UserVocabulary.user_id == current_user.id
    ).with_for_update())
    if user_vocab is None:
        raise HTTPException(status_code=404, detail="Saved vocabulary entry not found")
    now = datetime.now(timezone.utc)
    today = now.astimezone(VIETNAM).date()
    goals = db.scalars(select(DailyFlashcardGoal).where(
        DailyFlashcardGoal.user_id == current_user.id, DailyFlashcardGoal.activity_date == today)).all()
    if not goals:
        ids = db.scalars(select(UserVocabulary.id).where(
            UserVocabulary.user_id == current_user.id,
            or_(UserVocabulary.next_review_at.is_(None), UserVocabulary.next_review_at <= now),
        ).order_by(UserVocabulary.next_review_at.asc().nullsfirst(), UserVocabulary.id.asc()).limit(30)).all()
        goals = [DailyFlashcardGoal(user_id=current_user.id, activity_date=today, saved_id=card_id, completed=False) for card_id in ids]
        db.add_all(goals)
    goal = next((g for g in goals if g.saved_id == saved_id), None)
    if goal is None or goal.completed:
        raise HTTPException(status_code=409, detail="Flashcard is not in today's remaining review goal")
    was_due = user_vocab.next_review_at is None or user_vocab.next_review_at <= now
    if not was_due:
        raise HTTPException(status_code=409, detail="Flashcard is not due for review")
    apply_rating(user_vocab, body.rating, now)
    if body.rating != 'again':
        goal.completed = True
    if goals and all(g.completed for g in goals):
        record_learning_day(db, current_user.id, now)
    db.flush()
    if body.request_id is not None:
        # Store a snapshot, not the mutable card state from a later review.
        user_vocab.vocabulary  # load relationship before serializing
        result = UserVocabularyResponse.model_validate(user_vocab).model_dump(mode="json")
        db.add(FlashcardReviewRequest(user_id=current_user.id, request_id=body.request_id,
                                      saved_id=saved_id, rating=body.rating, response=result))
        db.commit()
        return result
    db.commit()
    db.refresh(user_vocab)
    return user_vocab
