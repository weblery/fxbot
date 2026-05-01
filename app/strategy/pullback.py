"""
Pullback detection — price retracing to EMA(20) on H1.

Logic:
  LONG pullback  → price dipped to/below EMA(20) then closed back above it
  SHORT pullback → price spiked to/above EMA(20) then closed back below it

This is deterministic — no Fibonacci, no multi-method mixing.
EMA calculated with pure pandas (no external library needed).
"""

from __future__ import annotations

import pandas as pd

from app.core.constants import TradeDirection
from app.core.logger import get_logger

logger = get_logger("strategy.pullback")


def _ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average using pandas."""
    return series.ewm(span=period, adjust=False).mean()


def detect_pullback(
    df: pd.DataFrame,
    trend_direction: TradeDirection,
    pullback_ema_period: int = 20,
    lookback: int = 5,
) -> bool:
    """Detect if price has pulled back to the EMA(20) zone.

    A pullback is confirmed when:
    - LONG: within the last `lookback` bars, the low touched/crossed below
            EMA(20), AND the most recent close is back above EMA(20).
    - SHORT: within the last `lookback` bars, the high touched/crossed above
             EMA(20), AND the most recent close is back below EMA(20).

    Args:
        df: OHLC DataFrame (H1 timeframe, closed candles only).
        trend_direction: Current trend from H4 analysis.
        pullback_ema_period: EMA period for pullback detection (default 20).
        lookback: How many recent bars to check for the pullback touch.

    Returns:
        True if a valid pullback is detected.
    """
    if len(df) < pullback_ema_period + lookback:
        return False

    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema = _ema(close, pullback_ema_period)

    # Check recent bars for pullback touch
    recent_slice = slice(-lookback, None)
    recent_ema = ema.iloc[recent_slice]
    recent_low = low.iloc[recent_slice]
    recent_high = high.iloc[recent_slice]
    current_close = close.iloc[-1]
    current_ema = ema.iloc[-1]

    if trend_direction == TradeDirection.LONG:
        # Price dipped to/below EMA, then closed above it
        touched_ema = (recent_low <= recent_ema).any()
        closed_above = current_close > current_ema
        pullback_detected = touched_ema and closed_above

    elif trend_direction == TradeDirection.SHORT:
        # Price spiked to/above EMA, then closed below it
        touched_ema = (recent_high >= recent_ema).any()
        closed_below = current_close < current_ema
        pullback_detected = touched_ema and closed_below

    else:
        pullback_detected = False

    logger.debug(
        "Pullback analysis",
        direction=trend_direction.value,
        pullback_detected=pullback_detected,
        current_close=round(current_close, 5),
        current_ema=round(current_ema, 5),
    )

    return pullback_detected
