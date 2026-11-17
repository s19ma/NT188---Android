import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.endpoints import (
    playback,
    progress,
    statistics,
    subtitles,
    admin,
    auth,
    quizzes,
    users,
    videos,
    vocabulary,
)
from app.core.config import settings
from app.db.database import engine, get_db
import app.models  # noqa: F401 — đăng ký tất cả ORM models vào Base.metadata
from app.models import (
    LearningProgress,
    Transcript,
    TranscriptSegment,
    User,
    UserVocabulary,
    Video,
    Vocabulary,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Backend API cho ứng dụng English Through Video",
)

# CORS — cho phép frontend (React/Vue/Android) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router API
app.include_router(users.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1")
app.include_router(playback.router, prefix="/api/v1")
app.include_router(subtitles.router, prefix="/api/v1")
app.include_router(vocabulary.router, prefix="/api/v1")
app.include_router(vocabulary.flashcard_router, prefix="/api/v1")
app.include_router(progress.router, prefix="/api/v1")
app.include_router(statistics.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(quizzes.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


# ──────────────────────────────────────────────
# Root & Health Check
# ──────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
def database_health_check():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database(), NOW()")
            )
            row = result.fetchone()
            return {
                "status": "connected",
                "database": row[0],
                "server_time": str(row[1]),
            }
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )


# ──────────────────────────────────────────────
# Kiểm tra khả năng truy vấn database qua ORM Models
# ──────────────────────────────────────────────
@app.get("/health/models")
def models_health_check(db: Session = Depends(get_db)):
    try:
        counts = {
            "users": db.query(User).count(),
            "videos": db.query(Video).count(),
            "transcripts": db.query(Transcript).count(),
            "transcript_segments": db.query(TranscriptSegment).count(),
            "vocabulary": db.query(Vocabulary).count(),
            "user_vocabulary": db.query(UserVocabulary).count(),
            "learning_progress": db.query(LearningProgress).count(),
        }
        return {
            "status": "all_models_synced",
            "table_counts": counts,
        }
    except Exception:
        logger.exception("Database model health check failed")
        raise HTTPException(
            status_code=500,
            detail="Model query test failed",
        )
