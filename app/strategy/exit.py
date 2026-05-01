"""
Exit calculation — ATR-based stop loss with min distance floor, RR-based take profit.

SL = entry ± max(ATR * multiplier, min_sl_pips * pip_size)
TP = entry ± (SL_distance * RR_ratio)

Direction-aware: LONG SL is below entry, SHORT SL is above entry.
"""

from __future__ import annotations

from app.core.constants import TradeDirection
from app.core.logger import get_logger

logger = get_logger("strategy.exit")


def calculate_stop_loss(
    entry_price: float,
    atr: float,
    direction: TradeDirection,
    atr_multiplier: float = 2.0,
    min_sl_distance: float = 0.0,
) -> float:
    """Calculate stop loss price with ATR and minimum distance floor.

    Args:
        entry_price: The trade entry price.
        atr: Current ATR value.
        direction: Trade direction.
        atr_multiplier: ATR multiplier for SL distance.
        min_sl_distance: Minimum SL distance in price units
                         (calculated externally as min_sl_pips * pip_size).

    Returns:
        Stop loss price.
    """
    atr_distance = atr * atr_multiplier
    sl_distance = max(atr_distance, min_sl_distance)

    if direction == TradeDirection.LONG:
        sl = entry_price - sl_distance
    else:
        sl = entry_price + sl_distance

    logger.debug(
        "SL calculated",
        direction=direction.value,
        entry=round(entry_price, 5),
        atr_distance=round(atr_distance, 5),
        min_sl_distance=round(min_sl_distance, 5),
        final_sl_distance=round(sl_distance, 5),
        sl=round(sl, 5),
    )

    return sl


def calculate_take_profit(
    entry_price: float,
    stop_loss: float,
    direction: TradeDirection,
    rr_ratio: float = 2.0,
) -> float:
    """Calculate take profit price based on risk-reward ratio.

    TP distance = SL distance * RR ratio

    Args:
        entry_price: The trade entry price.
        stop_loss: The stop loss price.
        direction: Trade direction.
        rr_ratio: Risk-reward ratio (default 2.0 = 2R).

    Returns:
        Take profit price.
    """
    sl_distance = abs(entry_price - stop_loss)
    tp_distance = sl_distance * rr_ratio

    if direction == TradeDirection.LONG:
        tp = entry_price + tp_distance
    else:
        tp = entry_price - tp_distance

    logger.debug(
        "TP calculated",
        direction=direction.value,
        sl_distance=round(sl_distance, 5),
        rr_ratio=rr_ratio,
        tp_distance=round(tp_distance, 5),
        tp=round(tp, 5),
    )

    return tp
