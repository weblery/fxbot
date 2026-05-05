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
        import MetaTrader5 as mt5
        logger.info(f"Preparing MT5 order for {order.symbol} ({order.direction.value})")
        
        action = mt5.TRADE_ACTION_DEAL
        order_type = mt5.ORDER_TYPE_BUY if order.direction.value == "long" else mt5.ORDER_TYPE_SELL
        
        # Ensure symbol is visible in Market Watch
        mt5.symbol_select(order.symbol, True)
        
        # Get current tick price
        tick = mt5.symbol_info_tick(order.symbol)
        if not tick:
            return OrderResult(success=False, message=f"Failed to get tick data for {order.symbol}")
            
        price = tick.ask if order.direction.value == "long" else tick.bid
        
        request = {
            "action": action,
            "symbol": order.symbol,
            "volume": float(order.lot_size),
            "type": order_type,
            "price": float(price),
            "sl": float(order.stop_loss),
            "tp": float(order.take_profit),
            "deviation": 20,
            "magic": 123456,
            "comment": "FOREXBOT_V3",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None:
            return OrderResult(success=False, message=f"order_send returned None. Error: {mt5.last_error()}")
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Order failed. Retcode: {result.retcode}, Comment: {result.comment}"
            logger.error(error_msg)
            return OrderResult(success=False, message=error_msg)
            
        logger.info(f"✅ Order successfully executed! Ticket: {result.order}")
        return OrderResult(success=True, ticket=result.order, message="Order executed successfully")

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
