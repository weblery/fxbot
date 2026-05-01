"""Tests for time utilities."""

from datetime import datetime, timezone
from app.utils.time_utils import is_in_session


class TestTimeUtils:
    def test_london_session(self):
        # 10:00 UTC — inside London (07:00-16:00)
        t = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert is_in_session(t, ["LONDON"]) is True

    def test_outside_london(self):
        # 05:00 UTC — outside London
        t = datetime(2025, 1, 15, 5, 0, tzinfo=timezone.utc)
        assert is_in_session(t, ["LONDON"]) is False

    def test_ny_session(self):
        # 15:00 UTC — inside NY (12:00-21:00)
        t = datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)
        assert is_in_session(t, ["NEW_YORK"]) is True

    def test_overlap_london_ny(self):
        # 14:00 UTC — inside both London and NY
        t = datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc)
        assert is_in_session(t, ["LONDON", "NEW_YORK"]) is True

    def test_asian_session_crosses_midnight(self):
        # 01:00 UTC — inside Asia (23:00-08:00)
        t = datetime(2025, 1, 15, 1, 0, tzinfo=timezone.utc)
        assert is_in_session(t, ["ASIA"]) is True

    def test_outside_all_sessions(self):
        # 22:00 UTC — between NY close and Asia open
        t = datetime(2025, 1, 15, 22, 0, tzinfo=timezone.utc)
        assert is_in_session(t, ["LONDON", "NEW_YORK"]) is False
