"""
run_live.py — Full live trading runner.
Syncs with MT5, monitors elite symbols, and executes trades automatically.
"""

import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.logger import get_logger
from app.data.mt5_client import MT5Client
from app.strategy.engine import StrategyEngine
from app.data.transformer import transform_raw_data
from app.execution.mt5_broker import MT5Broker

logger = get_logger("run_live")

def main():
    settings = get_settings()
    logger.info("🚀 INITIALIZING LIVE EXECUTION BOT...")
    logger.info(f"📊 Portfolio: {list(settings.symbols.keys())}")
    
    # 1. Connect to MT5
    # Credentials should be in .env or os environment variables
    client = MT5Client(
        login=int(sys.argv[1]) if len(sys.argv) > 1 else None,
        password=sys.argv[2] if len(sys.argv) > 2 else None,
        server=sys.argv[3] if len(sys.argv) > 3 else None
    )
    
    broker = MT5Broker()
    engine = StrategyEngine(settings)
    
    try:
        with client:
            if not client.is_connected:
                logger.error("❌ Failed to connect to MT5. Check credentials/Windows OS.")
                return

            logger.info("✅ Connection established. Bot is now active.")
            
            while True:
                now = datetime.now()
                # Check for signals at the start of every hour (or poll)
                if now.minute == 0 and now.second < 10:
                    logger.info(f"🔔 Hourly Scan Started: {now.strftime('%Y-%m-%d %H:%M')}")
                    
                    for symbol in settings.symbols.keys():
                        # Fetch live candles from MT5
                        h1_raw = broker.get_rates(symbol, "H1", count=300)
                        h4_raw = broker.get_rates(symbol, "H4", count=300)
                        
                        if h1_raw is None or h4_raw is None:
                            continue
                            
                        h1_df = transform_raw_data(h1_raw)
                        h4_df = transform_raw_data(h4_raw)
                        
                        # Run strategy
                        signal = engine.analyze(h1_df, h4_df, symbol, current_time=now)
                        
                        if signal:
                            logger.info(f"🔥 LIVE SIGNAL: {symbol} {signal.direction.value}")
                            # Execute Order
                            # result = broker.place_order(signal)
                            # logger.info(f"📝 Execution Result: {result}")
                    
                    # Cooldown to avoid multi-trigger in same minute
                    time.sleep(60)
                
                # Sleep and poll
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user.")
    except Exception as e:
        logger.exception(f"💥 CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
