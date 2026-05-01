"""
ATR (Average True Range) calculation — volatility measurement.
Implemented with pure pandas/numpy (no external indicator library needed).
Uses H1 timeframe data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.logger import get_logger

logger = get_logger("strategy.atr")


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """Calculate the current ATR value using Wilder's smoothing.

    ATR = EMA of True Range, where:
      True Range = max(high - low, |high - prev_close|, |low - prev_close|)

    Uses the most recent closed candle's ATR.

    Args:
        df: OHLC DataFrame (closed candles only).
        period: ATR lookback period (default 14).

    Returns:
        Current ATR value, or None if insufficient data.
    """
    if len(df) < period + 1:
        logger.debug(f"Insufficient data for ATR: {len(df)} bars, need {period + 1}")
        return None

    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Calculate True Range
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing (equivalent to EMA with alpha=1/period)
    atr_series = true_range.ewm(alpha=1.0 / period, adjust=False).mean()

    # Drop NaN values
    atr_series = atr_series.dropna()
    if len(atr_series) == 0:
        logger.warning("ATR calculation produced all NaN values")
        return None

    atr_value = float(atr_series.iloc[-1])

    logger.debug(f"ATR({period}) = {atr_value:.5f}")
    return atr_value
