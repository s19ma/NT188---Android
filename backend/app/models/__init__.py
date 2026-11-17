"""
SQLAlchemy Models — tự động import khi Alembic hoặc FastAPI khởi động.
Thứ tự import theo dependency (bảng độc lập trước).
"""
from app.models.user import User                          # noqa: F401
from app.models.video import Video                        # noqa: F401
from app.models.video_summary import VideoSummary         # noqa: F401
from app.models.transcript import Transcript              # noqa: F401
from app.models.transcript_segment import TranscriptSegment  # noqa: F401
from app.models.vocabulary import Vocabulary              # noqa: F401
from app.models.user_vocabulary import UserVocabulary     # noqa: F401
from app.models.learning_progress import LearningProgress # noqa: F401
from app.models.password_reset_otp import PasswordResetOtp # noqa: F401
from app.models.quiz_attempt import QuizAttempt # noqa: F401
from app.models.learning_day import LearningDay # noqa: F401
from app.models.daily_flashcard_goal import DailyFlashcardGoal # noqa: F401
from app.models.email_verification_otp import EmailVerificationOtp # noqa: F401
from app.models.email_outbox import EmailOutbox # noqa: F401
from app.models.flashcard_review_request import FlashcardReviewRequest # noqa: F401

__all__ = [
    "User",
    "Video",
    "VideoSummary",
    "Transcript",
    "TranscriptSegment",
    "Vocabulary",
    "UserVocabulary",
    "LearningProgress",
    "PasswordResetOtp",
    "QuizAttempt",
]
