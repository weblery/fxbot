"""
Position sizing — calculates lot size based on risk and stop distance.

Formula: position_size = risk_amount / (sl_pips * pip_value_per_lot)

Uses per-symbol contract_size for accurate pip value calculation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logger import get_logger
from app.utils.math_utils import get_pip_value, price_to_pips, round_lot_size

if TYPE_CHECKING:
    from app.core.config import SymbolConfig

logger = get_logger("risk.position_sizing")


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    sl_distance: float,
    symbol: str,
    symbols_config: dict[str, "SymbolConfig"],
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """Calculate position size (lot size) for a trade.

    Args:
        account_balance: Current account balance in account currency.
        risk_percent: Risk per trade as decimal (e.g., 0.02 = 2%).
        sl_distance: Stop loss distance in price units (not pips).
        symbol: Trading symbol.
        symbols_config: Symbol configuration dict.
        min_lot: Minimum allowed lot size.
        max_lot: Maximum allowed lot size.

    Returns:
        Position size in lots, rounded to valid broker increment.
    """
    if sl_distance <= 0:
        logger.error("SL distance must be positive")
        return min_lot

    # Calculate risk amount in account currency
    risk_amount = account_balance * risk_percent

    # Convert SL distance to pips
    sl_pips = price_to_pips(sl_distance, symbol, symbols_config)
    if sl_pips <= 0:
        logger.error("SL pips must be positive")
        return min_lot

    # Calculate pip value for 1 standard lot
    pip_value_per_lot = get_pip_value(symbol, 1.0, symbols_config)
    if pip_value_per_lot <= 0:
        logger.error("Pip value must be positive")
        return min_lot

    # Position size = risk / (SL in pips * pip value per lot)
    lot_size = risk_amount / (sl_pips * pip_value_per_lot)

    # Clamp to valid range
    lot_size = max(min_lot, min(lot_size, max_lot))

    # Round to valid increment
    lot_size = round_lot_size(lot_size, min_lot)

    logger.info(
        "Position size calculated",
        symbol=symbol,
        balance=account_balance,
        risk_pct=risk_percent,
        risk_amount=round(risk_amount, 2),
        sl_pips=round(sl_pips, 1),
        pip_value=round(pip_value_per_lot, 2),
        lot_size=lot_size,
    )

    return lot_size
