from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.services.streak import record_learning_day, streak_summary


@pytest.mark.parametrize(('offsets', 'expected'), [
    ([], 0), ([0], 1), ([-1], 1), ([-2], 0),
    ([0, -1, -2], 3), ([-1, -2], 2), ([0, -2], 1),
])
def test_streak_respects_consecutive_days_and_yesterday_grace(offsets, expected):
    today = date(2026, 11, 17)
    count, week = streak_summary([today + timedelta(days=n) for n in offsets], today)
    assert count == expected
    assert week[0][0] == date(2026, 11, 16)
    assert week[1] == (today, 0 in offsets)


@pytest.mark.parametrize(('hour', 'minute', 'expected'), [
    (16, 59, date(2026, 11, 16)),
    (17, 0, date(2026, 11, 17)),
])
def test_learning_day_uses_vietnam_midnight(hour, minute, expected):
    db = Mock()
    record_learning_day(db, '00000000-0000-0000-0000-000000000001',
                        datetime(2026, 11, 16, hour, minute, tzinfo=timezone.utc))
    statement = db.execute.call_args.args[0]
    assert statement.compile(dialect=postgresql.dialect()).params['activity_date'] == expected
