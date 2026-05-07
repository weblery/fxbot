"""
Broker interface — abstract base class for broker implementations.
Enables swapping MT5 for REST/FIX/crypto exchanges without rewriting strategy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

from app.core.constants import TradeDirection
from app.models.position import Position


@dataclass
class Order:
    symbol: str
    direction: TradeDirection
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float


@dataclass
class OrderResult:
    success: bool
    ticket: Optional[int] = None
    message: str = ""


@dataclass
class AccountInfo:
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0


class BrokerInterface(ABC):
    """Abstract broker interface — all broker implementations extend this."""

    @abstractmethod
    def send_order(self, order: Order) -> OrderResult: ...

    @abstractmethod
    def modify_order(self, ticket: int, sl: float, tp: float) -> bool: ...

    @abstractmethod
    def close_position(self, ticket: int) -> bool: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_account_info(self) -> AccountInfo: ...
