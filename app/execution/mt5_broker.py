"""
MT5 Broker — concrete implementation of BrokerInterface for MetaTrader 5.
Stubbed for Phase 1. Will be implemented in Phase 3.
"""

from __future__ import annotations

from app.core.logger import get_logger
from app.execution.broker import BrokerInterface, Order, OrderResult, AccountInfo
from app.models.position import Position

logger = get_logger("execution.mt5_broker")


class MT5Broker(BrokerInterface):
    """MetaTrader 5 broker implementation (Phase 3)."""

    def send_order(self, order: Order) -> OrderResult:
        logger.warning("MT5Broker.send_order() is a stub — Phase 3")
        return OrderResult(success=False, message="Not implemented")

    def modify_order(self, ticket: int, sl: float, tp: float) -> bool:
        logger.warning("MT5Broker.modify_order() is a stub — Phase 3")
        return False

    def close_position(self, ticket: int) -> bool:
        logger.warning("MT5Broker.close_position() is a stub — Phase 3")
        return False

    def get_positions(self) -> list[Position]:
        logger.warning("MT5Broker.get_positions() is a stub — Phase 3")
        return []

    def get_account_info(self) -> AccountInfo:
        logger.warning("MT5Broker.get_account_info() is a stub — Phase 3")
        return AccountInfo()
