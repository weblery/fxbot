"""
Position data model — represents a live or historical trading position.
Used by execution layer and analytics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.constants import TradeDirection, TradeState


@dataclass
class Position:
    """A trading position tracked through its lifecycle.

    Created when an order is filled, updated as SL/TP are modified,
    closed when the trade exits.
    """
    ticket: int                       # Broker-assigned order ID
    symbol: str
    direction: TradeDirection
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    state: TradeState = TradeState.OPEN
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    pnl: Optional[float] = None

    @property
    def is_open(self) -> bool:
        return self.state == TradeState.OPEN

    @property
    def is_closed(self) -> bool:
        return self.state in (
            TradeState.STOPPED,
            TradeState.TARGET_HIT,
            TradeState.CLOSED,
        )
