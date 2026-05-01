"""
Core constants and enums used across all modules.
Every enum lives here — no magic strings anywhere in the codebase.
"""

from enum import Enum


class TradeDirection(str, Enum):
    """Direction of a trade signal."""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeState(str, Enum):
    """Lifecycle state of a trade."""
    PENDING = "PENDING"          # Signal generated, not yet executed
    OPEN = "OPEN"                # Position is live
    STOPPED = "STOPPED"          # Hit stop loss
    TARGET_HIT = "TARGET_HIT"    # Hit take profit
    CLOSED = "CLOSED"            # Manually closed or expired


class SignalStrength(str, Enum):
    """Confidence level of a trade signal."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class ExecutionMode(str, Enum):
    """Backtest candle ambiguity resolution mode."""
    CONSERVATIVE = "conservative"   # SL checked first (worst case)
    OPTIMISTIC = "optimistic"       # TP checked first (best case)
    RANDOM = "random"               # Randomly weighted (realistic range)


class TradingSession(str, Enum):
    """Major forex trading sessions."""
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    ASIA = "ASIA"


class Timeframe(str, Enum):
    """Supported chart timeframes."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


# MT5 timeframe mapping (used by data layer)
# Maps our Timeframe enum to MT5 integer constants
MT5_TIMEFRAME_MAP = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1: 16385,
    Timeframe.H4: 16388,
    Timeframe.D1: 16408,
    Timeframe.W1: 32769,
    Timeframe.MN1: 49153,
}
