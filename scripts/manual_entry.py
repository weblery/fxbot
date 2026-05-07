import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.execution.mt5_broker import MT5Broker
from app.execution.broker import Order
from app.core.constants import TradeDirection
from app.data.mt5_client import MT5Client
from app.core.logger import setup_logging, get_logger

logger = get_logger("scripts.manual_entry")

def main():
    parser = argparse.ArgumentParser(description="🚀 FOREXBOT Manual Trade Entry")
    parser.add_argument("--symbol", required=True, help="Symbol to trade (e.g., NZDUSDm)")
    parser.add_argument("--dir", choices=["LONG", "SHORT"], required=True, help="Direction (LONG/SHORT)")
    parser.add_argument("--lots", type=float, default=0.01, help="Lot size (default: 0.01)")
    parser.add_argument("--sl", type=float, help="Stop Loss price (absolute)")
    parser.add_argument("--tp", type=float, help="Take Profit price (absolute)")
    
    args = parser.parse_args()
    
    # Initialize logging
    setup_logging(level="INFO", log_format="text")
    
    logger.info(f"Initiating manual trade: {args.dir} {args.lots} lots on {args.symbol}")

    # 1. Connect to MT5
    # Assumes credentials are in .env or passed via env vars
    with MT5Client() as client:
        if not client.is_connected:
            logger.error("❌ MT5 Connection Failed. Check if MT5 is open on your Windows machine.")
            return

        broker = MT5Broker()
        direction = TradeDirection.LONG if args.dir == "LONG" else TradeDirection.SHORT
        
        # 2. Build Order 
        # Note: entry_price=0.0 tells the MT5Broker to use current market Ask/Bid
        order = Order(
            symbol=args.symbol,
            direction=direction,
            lot_size=args.lots,
            entry_price=0.0, 
            stop_loss=args.sl or 0.0,
            take_profit=args.tp or 0.0
        )

        # 3. Execute
        logger.info(f"📤 Sending order to MT5...")
        result = broker.send_order(order)
        
        if result.success:
            logger.info(f"✅ MANUAL ENTRY SUCCESS! Ticket: {result.ticket}")
        else:
            logger.error(f"❌ MANUAL ENTRY FAILED: {result.message}")

if __name__ == "__main__":
    main()
