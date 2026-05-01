"""
Trend detection — EMA-based only (v1, locked).

Logic:
  LONG  → EMA(50) > EMA(200) AND EMA(50) slope is positive
  SHORT → EMA(50) < EMA(200) AND EMA(50) slope is negative
  None  → No clear trend (EMAs flat or crossing)

Uses H4 timeframe data for higher-timeframe confirmation.
EMA calculated with pure pandas (no external indicator library needed).
"""

from __future__ import annotations

import pandas as pd

from app.core.constants import TradeDirection
from app.core.logger import get_logger

logger = get_logger("strategy.trend")


def _ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average using pandas."""
    return series.ewm(span=period, adjust=False).mean()


def detect_trend(
    df: pd.DataFrame,
    ema_fast_period: int = 50,
    ema_slow_period: int = 200,
    slope_lookback: int = 5,
) -> TradeDirection | None:
    """Detect market trend direction using EMA crossover and slope.

    Uses CLOSED candles only — the DataFrame must NOT include the current
    forming candle.

    Args:
        df: OHLC DataFrame (H4 timeframe, closed candles only).
        ema_fast_period: Fast EMA period (default 50).
        ema_slow_period: Slow EMA period (default 200).
        slope_lookback: Number of bars to measure EMA slope over.

    Returns:
        TradeDirection.LONG, TradeDirection.SHORT, or None.
    """
    if len(df) < ema_slow_period + slope_lookback:
        logger.debug(
            f"Insufficient data for trend detection: {len(df)} bars, "
            f"need {ema_slow_period + slope_lookback}"
        )
        return None

    close = df["close"]

    # Calculate EMAs using pure pandas
    ema_fast = _ema(close, ema_fast_period)
    ema_slow = _ema(close, ema_slow_period)

    # Get latest values
    current_fast = ema_fast.iloc[-1]
    current_slow = ema_slow.iloc[-1]
    previous_fast = ema_fast.iloc[-slope_lookback]

    # Calculate slope (normalized by price to make it comparable across symbols)
    price = close.iloc[-1]
    slope = (current_fast - previous_fast) / price if price != 0 else 0

    # Determine trend
    if current_fast > current_slow and slope > 0:
        direction = TradeDirection.LONG
    elif current_fast < current_slow and slope < 0:
        direction = TradeDirection.SHORT
    else:
        direction = None

    logger.debug(
        "Trend analysis complete",
        ema_fast=round(current_fast, 5),
        ema_slow=round(current_slow, 5),
        slope=round(slope, 6),
        direction=direction.value if direction else "NONE",
    )

    return direction
