"""
Time utilities — session detection and timestamp helpers.

Session times (UTC):
  LONDON:   07:00 — 16:00
  NEW_YORK: 12:00 — 21:00
  ASIA:     23:00 — 08:00 (crosses midnight)
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import NamedTuple

from app.core.constants import TradingSession


class SessionWindow(NamedTuple):
    """A trading session defined by UTC start and end times."""
    start: time
    end: time
    crosses_midnight: bool


# Session definitions (UTC)
SESSION_TIMES: dict[TradingSession, SessionWindow] = {
    TradingSession.LONDON: SessionWindow(
        start=time(7, 0), end=time(16, 0), crosses_midnight=False
    ),
    TradingSession.NEW_YORK: SessionWindow(
        start=time(12, 0), end=time(21, 0), crosses_midnight=False
    ),
    TradingSession.ASIA: SessionWindow(
        start=time(23, 0), end=time(8, 0), crosses_midnight=True
    ),
}


def get_session_times(session: TradingSession) -> SessionWindow:
    """Get the UTC time window for a trading session.

    Args:
        session: The trading session.

    Returns:
        SessionWindow with start, end, and midnight crossing info.
    """
    return SESSION_TIMES[session]


def is_in_session(
    timestamp: datetime,
    sessions: list[str],
) -> bool:
    """Check if a timestamp falls within any of the specified trading sessions.

    Args:
        timestamp: The datetime to check (will be converted to UTC).
        sessions: List of session names (e.g., ['LONDON', 'NEW_YORK']).

    Returns:
        True if the timestamp is within at least one specified session.
    """
    # Ensure we're working in UTC
    if timestamp.tzinfo is None:
        utc_time = timestamp.time()
    else:
        utc_time = timestamp.astimezone(timezone.utc).time()

    for session_name in sessions:
        try:
            session = TradingSession(session_name)
        except ValueError:
            continue

        window = SESSION_TIMES[session]

        if window.crosses_midnight:
            # Session spans midnight (e.g., ASIA: 23:00 → 08:00)
            if utc_time >= window.start or utc_time <= window.end:
                return True
        else:
            # Normal session (e.g., LONDON: 07:00 → 16:00)
            if window.start <= utc_time <= window.end:
                return True

    return False


def to_utc(dt: datetime) -> datetime:
    """Convert a datetime to UTC. If naive, assumes UTC.

    Args:
        dt: Input datetime.

    Returns:
        UTC datetime.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
