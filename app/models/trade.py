"""
Trade data models — used across strategy, backtesting, execution, and analytics.

TradeIdea: output of strategy engine (what to trade)
TradeResult: outcome of a trade (what happened)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.constants import TradeDirection, TradeState


@dataclass
class TradeIdea:
    """A potential trade identified by the strategy engine.

    Generated from closed candle data only.
    Entry price is the NEXT candle's open (not the signal candle's close).
    """
    symbol: str
    direction: TradeDirection
    entry_price: float               # Next candle open + spread + slippage
    stop_loss: float
    take_profit: float | None        # None for trailing stop strategies
    atr: float
    risk_reward: float
    timestamp: datetime              # Time the signal was generated
    reasoning: dict[str, Any] = field(default_factory=dict)

    @property
    def sl_distance(self) -> float:
        """Absolute distance from entry to stop loss."""
        return abs(self.entry_price - self.stop_loss)

    @property
    def tp_distance(self) -> float:
        """Absolute distance from entry to take profit."""
        return abs(self.take_profit - self.entry_price)


@dataclass
class TradeResult:
    """The outcome of an executed trade (live or simulated).

    Tracks the full lifecycle from entry to exit.
    """
    trade_idea: TradeIdea
    state: TradeState
    exit_price: float | None = None
    pnl: float | None = None         # Profit/loss in account currency
    pnl_pips: float | None = None    # Profit/loss in pips
    exit_time: datetime | None = None
    highest_high: float | None = None # Track max adverse/favorable excursion
    lowest_low: float | None = None

    @property
    def is_winner(self) -> bool:
        """True if trade was profitable."""
        return self.pnl is not None and self.pnl > 0

    @property
    def is_closed(self) -> bool:
        """True if trade has reached a terminal state."""
        return self.state in (
            TradeState.STOPPED,
            TradeState.TARGET_HIT,
            TradeState.CLOSED,
        )
