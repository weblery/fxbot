"""
watch_signals.py — Real-time signal monitoring for the Elite Portfolio.
Polls MT5 (or stubs) for live candles and alerts on breakout detections.
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

logger = get_logger("watch_signals")

def fetch_live_data(symbol, timeframe, count=300):
    """
    In a real Windows environment, this would call mt5.copy_rates_from_pos.
    On Mac, we simulate with the last few lines of our historical CSVs 
    to demonstrate the logic.
    """
    # Placeholder for real MT5 integration
    # if mt5_connected: return mt5_data
    
    # For now, we use our resampled H1/H4 files to simulate 'Live'
    data_path = Path(f"data/{symbol}_{timeframe}.csv")
    if not data_path.exists():
        return None
    
    import pandas as pd
    df = pd.read_csv(data_path)
    return df.tail(count)

def main():
    settings = get_settings()
    logger.info("🚀 Starting Real-Time Signal Watcher...")
    logger.info(f"📈 Monitoring {len(settings.symbols)} Elite Symbols")
    
    engine = StrategyEngine()
    
    # Symbols to watch
    symbols = list(settings.symbols.keys())
    
    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\r[{now}] 🔍 Scanning markets...", end="", flush=True)
            
            for symbol in symbols:
                # 1. Fetch 'Live' Data (Last 100 bars)
                h1_raw = fetch_live_data(symbol, "H1")
                h4_raw = fetch_live_data(symbol, "H4")
                
                if h1_raw is None or h4_raw is None:
                    continue
                
                # 2. Transform to model format
                h1_data = transform_raw_data(h1_raw)
                h4_data = transform_raw_data(h4_raw)
                
                # 3. Run Strategy for CURRENT bar
                # We check the very last candle in the data
                last_time = h1_data["time"].iloc[-1]
                signal = engine.analyze(h1_data, h4_data, symbol, current_time=last_time)
                
                if signal:
                    logger.info(f"🔔 SIGNAL DETECTED: {symbol} | {signal.direction.value} @ {signal.entry_price}")
                    logger.info(f"   🎯 Target: {signal.take_profit} | 🛡️ Stop: {signal.stop_loss}")
                    # In Phase 3, this is where we would call execution_manager.place_order()
            
            # Wait 60 seconds before next scan
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Signal Watcher stopped by user.")

if __name__ == "__main__":
    main()
