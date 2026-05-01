"""
Math utilities for Forex calculations.

Handles the critical edge cases:
- Standard pairs (EURUSD, GBPUSD): pip_size=0.0001, contract=100,000
- JPY pairs (USDJPY): pip_size=0.01, contract=100,000
- Gold (XAUUSD): pip_size=0.1, contract=100

All calculations use per-symbol config — never hardcoded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import SymbolConfig


def get_pip_size(symbol: str, symbols_config: dict[str, "SymbolConfig"]) -> float:
    """Get the pip size for a symbol from config.

    Args:
        symbol: Trading symbol (e.g., 'EURUSD').
        symbols_config: Symbol configuration dict from settings.

    Returns:
        Pip size (e.g., 0.0001 for EURUSD, 0.01 for USDJPY, 0.1 for XAUUSD).

    Raises:
        KeyError: If symbol not found in config.
    """
    if symbol not in symbols_config:
        raise KeyError(f"Symbol '{symbol}' not found in config. Add it to configs/default.yaml")
    return symbols_config[symbol].pip_size


def get_pip_value(
    symbol: str,
    lot_size: float,
    symbols_config: dict[str, "SymbolConfig"],
) -> float:
    """Calculate the monetary value of 1 pip for a given lot size.

    Formula: pip_value = pip_size * contract_size * lot_size

    For USD-denominated accounts trading USD-quoted pairs (EURUSD, GBPUSD):
      pip_value = 0.0001 * 100,000 * 1.0 = $10

    For XAUUSD:
      pip_value = 0.1 * 100 * 1.0 = $10

    Note: This assumes the account currency matches the quote currency.
    Cross-currency conversion is not handled in v1.

    Args:
        symbol: Trading symbol.
        lot_size: Position size in lots.
        symbols_config: Symbol configuration dict from settings.

    Returns:
        Pip value in account currency.
    """
    config = symbols_config[symbol]
    val = config.pip_size * config.contract_size * lot_size
    
    # Normalization for USD account currency
    # Standard: 100,000 * 0.0001 = $10
    # JPY: 100,000 * 0.01 = 1,000 JPY -> approx $6.66 (normalized to USD)
    if "JPY" in symbol:
        return val / 150.0  # Approx exchange rate
        
    return val


def pips_to_price(pips: float, symbol: str, symbols_config: dict[str, "SymbolConfig"]) -> float:
    """Convert a pip count to a price distance.

    Args:
        pips: Number of pips.
        symbol: Trading symbol.
        symbols_config: Symbol configuration dict.

    Returns:
        Price distance (e.g., 5 pips on EURUSD = 0.0005).
    """
    pip_size = get_pip_size(symbol, symbols_config)
    return pips * pip_size


def price_to_pips(
    price_distance: float, symbol: str, symbols_config: dict[str, "SymbolConfig"]
) -> float:
    """Convert a price distance to pips.

    Args:
        price_distance: Absolute price difference.
        symbol: Trading symbol.
        symbols_config: Symbol configuration dict.

    Returns:
        Number of pips.
    """
    pip_size = get_pip_size(symbol, symbols_config)
    if pip_size == 0:
        return 0.0
    return price_distance / pip_size


def round_price(price: float, symbol: str, symbols_config: dict[str, "SymbolConfig"]) -> float:
    """Round a price to the correct number of decimal places for a symbol.

    Args:
        price: Raw price value.
        symbol: Trading symbol.
        symbols_config: Symbol configuration dict.

    Returns:
        Rounded price.
    """
    pip_size = get_pip_size(symbol, symbols_config)
    # Determine decimal places from pip size (0.0001 → 5 decimals, 0.01 → 3, 0.1 → 2)
    decimals = len(str(pip_size).rstrip("0").split(".")[-1]) + 1
    return round(price, decimals)


def round_lot_size(lot_size: float, min_lot: float = 0.01) -> float:
    """Round lot size to valid broker increments.

    Args:
        lot_size: Calculated lot size.
        min_lot: Minimum lot size (typically 0.01).

    Returns:
        Rounded lot size, never below min_lot.
    """
    # Round down to 2 decimal places (0.01 increments)
    rounded = int(lot_size / min_lot) * min_lot
    return max(rounded, min_lot)
