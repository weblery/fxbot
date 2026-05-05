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
from app.execution.broker import Order
from app.data.mt5_client import MT5Client
from app.core.constants import Timeframe
from app.data.fetcher import DataFetcher
from app.strategy.engine import StrategyEngine
from app.data.transformer import transform_raw_data
from app.execution.mt5_broker import MT5Broker
from app.services.telegram import send_telegram_message, send_heartbeat

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
    fetcher = DataFetcher(client)
    
    try:
        with client:
            if not client.is_connected:
                logger.error("❌ Failed to connect to MT5. Check credentials/Windows OS.")
                return

            logger.info("✅ Connection established. Bot is now active.")
            
            # 2. Startup Telegram Alert
            send_telegram_message(
                f"🚀 *System Started*\n"
                f"Portfolio: {', '.join(settings.symbols.keys())}\n"
                f"Timeframe: {settings.timeframes.execution}\n"
                f"Heartbeat: every {settings.heartbeat_hours} hours."
            )
            
            last_heartbeat = datetime.now()
            
            while True:
                now = datetime.now()
                
                # 3. Heartbeat Checker
                hours_since_last = (now - last_heartbeat).total_seconds() / 3600
                if hours_since_last >= settings.heartbeat_hours:
                    send_heartbeat(list(settings.symbols.keys()))
                    last_heartbeat = now

                # 4. Hourly Scan
                # Check for signals at 10 minutes past every hour (maximum safety for sync)
                if now.minute == 10 and now.second < 10:
                    logger.info(f"🔔 Hourly Scan Started: {now.strftime('%Y-%m-%d %H:%M')}")
                    
                    for symbol in settings.symbols.keys():
                        # Fetch live candles from MT5
                        h1_raw = fetcher.fetch_ohlc(symbol, Timeframe.H1, num_bars=300)
                        h4_raw = fetcher.fetch_ohlc(symbol, Timeframe.H4, num_bars=300)
                        
                        if h1_raw is None or h4_raw is None or h1_raw.empty or h4_raw.empty:
                            continue
                            
                        h1_df = transform_raw_data(h1_raw)
                        h4_df = transform_raw_data(h4_raw)
                        
                        # Run strategy
                        signal = engine.analyze(h1_df, h4_df, symbol, current_time=now)
                        
                        if signal:
                            logger.info(f"🔥 LIVE SIGNAL: {symbol} {signal.direction.value}")
                            
                            # Safely construct the live order with a micro-lot (0.01)
                            order = Order(
                                symbol=symbol,
                                direction=signal.direction,
                                lot_size=0.01,
                                entry_price=signal.trade_idea.entry_price,
                                stop_loss=signal.trade_idea.stop_loss,
                                take_profit=signal.trade_idea.take_profit
                            )
                            
                            # Execute Order via MT5!
                            result = broker.send_order(order)
                            logger.info(f"📝 Execution Result: {result.message}")

                            # 5. Telegram Trade Alert
                            if result.success:
                                send_telegram_message(
                                    f"🔥 *LIVE TRADE EXECUTED*\n"
                                    f"Symbol: {symbol}\n"
                                    f"Direction: {signal.direction.value.upper()}\n"
                                    f"Price: {signal.entry_price}\n"
                                    f"SL: {signal.stop_loss}\n"
                                    f"TP: {signal.take_profit}"
                                )
                            else:
                                send_telegram_message(
                                    f"⚠️ *ORDER FAILED*\n"
                                    f"Symbol: {symbol}\n"
                                    f"Error: {result.message}"
                                )
                    
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
