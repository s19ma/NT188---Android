"""Lịch ôn theo mức đánh giá cố định.

Quality map:
- again = 1: quên, đưa lại sau 10 phút, reset chuỗi đúng
- hard  = 3: nhớ khó, ease giảm, vẫn tính là ôn đúng
- good  = 4: nhớ bình thường
- easy  = 5: nhớ dễ, ease tăng

Khó hẹn 1 ngày, tốt 3 ngày, dễ 7 ngày. Từ được coi là đã học
khi có ít nhất 4 lần trả lời đúng liên tiếp.
"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

RATING_QUALITY = {
    "again": 1,
    "hard": 3,
    "good": 4,
    "easy": 5,
}
LEARNED_INTERVAL_DAYS = 21
LEARNED_REPETITIONS = 4
RATING_INTERVAL_DAYS = {"hard": 1, "good": 3, "easy": 7}
MIN_EASE = Decimal("1.30")


def _ease_after_quality(ease: Decimal, quality: int) -> Decimal:
    q = Decimal(quality)
    gap = Decimal(5) - q
    delta = Decimal("0.1") - gap * (Decimal("0.08") + gap * Decimal("0.02"))
    updated = ease + delta
    if updated < MIN_EASE:
        updated = MIN_EASE
    return updated.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_rating(card, rating: str, now: datetime) -> None:
    quality = RATING_QUALITY[rating]
    ease = Decimal(str(card.ease_factor if card.ease_factor is not None else "2.50"))
    ease = _ease_after_quality(ease, quality)

    repetitions = int(card.repetitions or 0)

    if quality < 3:
        repetitions = 0
        interval = 0
        next_review = now + timedelta(minutes=10)
        status = "learning"
    else:
        interval = RATING_INTERVAL_DAYS[rating]
        repetitions += 1
        next_review = now + timedelta(days=interval)
        status = "learned" if repetitions >= LEARNED_REPETITIONS else "learning"

    card.ease_factor = ease
    card.repetitions = repetitions
    card.interval_days = interval
    card.next_review_at = next_review
    card.last_reviewed_at = now
    card.learning_status = status
    card.review_count = int(card.review_count or 0) + 1


def apply_learning_status(card, status: str, now: datetime) -> None:
    """Gán trạng thái thủ công và chỉnh lịch cho khớp nhãn."""
    if status == "new":
        card.learning_status = "new"
        card.ease_factor = Decimal("2.50")
        card.interval_days = 0
        card.repetitions = 0
        card.next_review_at = now
        card.last_reviewed_at = None
        return

    if status == "learned":
        interval = max(int(card.interval_days or 0), LEARNED_INTERVAL_DAYS)
        card.learning_status = "learned"
        card.interval_days = interval
        card.repetitions = max(int(card.repetitions or 0), 4)
        card.next_review_at = now + timedelta(days=interval)
        return

    card.learning_status = "learning"
    if card.next_review_at is None:
        card.next_review_at = now
