"""
Signal data model — wraps a TradeIdea with metadata for the signal pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.constants import SignalStrength, TradeDirection
from app.models.trade import TradeIdea


@dataclass
class Signal:
    """An actionable trade signal ready for risk validation and execution.

    Produced by the signal generator, consumed by the risk manager.
    """
    symbol: str
    direction: TradeDirection
    strength: SignalStrength
    trade_idea: TradeIdea
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_strong(self) -> bool:
        """True if signal meets minimum strength threshold."""
        return self.strength == SignalStrength.STRONG
