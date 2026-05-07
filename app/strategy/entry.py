"""
Entry confirmation — validates candle quality before allowing a trade.

Gates:
  1. Candle closes in trend direction (LONG → close > open, SHORT → close < open)
  2. Candle body ratio >= min_body_ratio (removes weak/indecision candles)

Entry price is NOT the signal candle's close — it's the NEXT candle's open.
This function validates whether the signal candle qualifies.
"""

from __future__ import annotations

import pandas as pd

from app.core.constants import TradeDirection
from app.core.logger import get_logger

logger = get_logger("strategy.entry")


def check_entry(
    df: pd.DataFrame,
    trend_direction: TradeDirection,
    min_body_ratio: float = 0.6,
) -> Optional[float]:
    """Check if the most recent closed candle confirms a valid entry.

    The entry price returned is the CLOSE of the signal candle.
    The backtest engine must use the NEXT candle's OPEN as the actual entry.

    Args:
        df: OHLC DataFrame (closed candles only).
        trend_direction: Current trend direction.
        min_body_ratio: Minimum candle body / total range ratio (0.0 to 1.0).

    Returns:
        Signal candle close price if entry is valid, None otherwise.
    """
    if len(df) < 2:
        return None

    candle = df.iloc[-1]
    open_price = candle["open"]
    close_price = candle["close"]
    high = candle["high"]
    low = candle["low"]

    # Gate 1: Candle closes in trend direction
    if trend_direction == TradeDirection.LONG and close_price <= open_price:
        logger.debug("Entry rejected: bearish candle in LONG trend")
        return None

    if trend_direction == TradeDirection.SHORT and close_price >= open_price:
        logger.debug("Entry rejected: bullish candle in SHORT trend")
        return None

    # Gate 2: Candle body ratio check
    candle_range = high - low
    if candle_range == 0:
        logger.debug("Entry rejected: zero-range candle (doji)")
        return None

    body = abs(close_price - open_price)
    body_ratio = body / candle_range

    if body_ratio < min_body_ratio:
        logger.debug(
            f"Entry rejected: body ratio {body_ratio:.2f} < {min_body_ratio}",
            body_ratio=round(body_ratio, 3),
        )
        return None

    logger.debug(
        "Entry confirmed",
        direction=trend_direction.value,
        close=round(close_price, 5),
        body_ratio=round(body_ratio, 3),
    )

    # Return signal candle close — actual entry uses NEXT candle open
    return float(close_price)
