from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.services.review_scheduler import apply_rating


def card(**changes):
    values = dict(
        ease_factor=Decimal("2.50"), interval_days=0, repetitions=0,
        review_count=0, next_review_at=None, last_reviewed_at=None,
        learning_status="new",
    )
    values.update(changes)
    return SimpleNamespace(**values)


class ReviewSchedulerTests(unittest.TestCase):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_again_resets_repetitions_and_is_due_in_ten_minutes(self):
        value = card(repetitions=3, interval_days=12)
        apply_rating(value, "again", self.now)
        self.assertEqual(0, value.repetitions)
        self.assertEqual(0, value.interval_days)
        self.assertEqual("learning", value.learning_status)
        self.assertEqual(self.now.minute + 10, value.next_review_at.minute)
        self.assertEqual(1, value.review_count)

    def test_hard_first_success_is_scheduled_for_one_day(self):
        value = card()
        apply_rating(value, "hard", self.now)
        self.assertEqual(1, value.repetitions)
        self.assertEqual(1, value.interval_days)
        self.assertEqual(self.now.day + 1, value.next_review_at.day)
        self.assertEqual(1, value.review_count)

    def test_good_is_scheduled_for_three_days(self):
        value = card(repetitions=1, interval_days=1)
        apply_rating(value, "good", self.now)
        self.assertEqual(2, value.repetitions)
        self.assertEqual(3, value.interval_days)
        self.assertEqual(self.now.day + 3, value.next_review_at.day)

    def test_easy_keeps_ease_above_minimum_and_counts_one_review(self):
        value = card(ease_factor=Decimal("1.30"), repetitions=2, interval_days=10)
        apply_rating(value, "easy", self.now)
        self.assertGreaterEqual(value.ease_factor, Decimal("1.30"))
        self.assertEqual(7, value.interval_days)
        self.assertEqual(1, value.review_count)

    def test_utc_duration_across_dst_transition(self):
        now = datetime(2026, 3, 7, 17, 0, tzinfo=timezone.utc)
        value = card()
        apply_rating(value, "good", now)
        self.assertEqual(timedelta(days=3), value.next_review_at - now)
        self.assertEqual(13, value.next_review_at.astimezone(ZoneInfo("America/New_York")).hour)

    def test_fixed_intervals_do_not_depend_on_prior_schedule(self):
        for rating, days in (("hard", 1), ("good", 3), ("easy", 7)):
            for repetitions in (0, 1, 3, 8):
                with self.subTest(rating=rating, repetitions=repetitions):
                    value = card(repetitions=repetitions, interval_days=30)
                    apply_rating(value, rating, self.now)
                    self.assertEqual(days, value.interval_days)
                    self.assertEqual(timedelta(days=days), value.next_review_at - self.now)

    def test_four_consecutive_successes_mark_learned_and_again_resets(self):
        value = card()
        for rating in ("hard", "good", "easy"):
            apply_rating(value, rating, self.now)
            self.assertEqual("learning", value.learning_status)
        apply_rating(value, "good", self.now)
        self.assertEqual(4, value.repetitions)
        self.assertEqual("learned", value.learning_status)
        apply_rating(value, "again", self.now)
        self.assertEqual(0, value.repetitions)
        self.assertEqual("learning", value.learning_status)


if __name__ == "__main__":
    unittest.main()
