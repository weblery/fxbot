"""
download_data.py — Fetch or generate historical OHLC data for backtesting.

Options:
  1. Generate realistic synthetic data (works immediately, no account needed)
  2. Download from MT5 (requires Windows + MT5 terminal + demo account)

Usage:
    # Generate synthetic data for testing
    python scripts/download_data.py --mode synthetic --symbol EURUSD --days 500

    # Download from MT5 (Windows only)
    python scripts/download_data.py --mode mt5 --symbol EURUSD --days 500
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logger import get_logger

logger = get_logger("scripts.download_data")


# ═══════════════════════════════════════════════════════════════
#  Realistic synthetic data generator
# ═══════════════════════════════════════════════════════════════

# Realistic volatility parameters (approximate daily ATR in price units)
SYMBOL_PARAMS = {
    "EURUSD": {
        "start_price": 1.0850,
        "daily_volatility": 0.0060,   # ~60 pips daily range
        "pip_size": 0.0001,
        "spread": 0.00015,
    },
    "GBPUSD": {
        "start_price": 1.2650,
        "daily_volatility": 0.0080,   # ~80 pips daily range
        "pip_size": 0.0001,
        "spread": 0.00020,
    },
    "XAUUSD": {
        "start_price": 2340.00,
        "daily_volatility": 25.0,     # ~$25 daily range
        "pip_size": 0.1,
        "spread": 0.30,
    },
}


def _generate_h1_data(
    symbol: str,
    days: int = 500,
    start_date: datetime | None = None,
) -> pd.DataFrame:
    """Generate realistic H1 OHLC data using geometric Brownian motion.

    Creates data that mimics real forex behavior:
    - Trends that last 20-60 bars
    - Mean reversion
    - Higher volatility during London/NY overlap
    - Lower volatility during Asian session
    - Weekend gaps (no Saturday/Sunday data)

    Args:
        symbol: Trading symbol.
        days: Number of trading days to generate.
        start_date: Start date for the data.

    Returns:
        DataFrame with columns: time, open, high, low, close, volume
    """
    params = SYMBOL_PARAMS.get(symbol)
    if params is None:
        print(f"❌ Unknown symbol: {symbol}. Supported: {list(SYMBOL_PARAMS.keys())}")
        sys.exit(1)

    if start_date is None:
        start_date = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    np.random.seed(42)  # Reproducible for consistent testing

    price = params["start_price"]
    hourly_vol = params["daily_volatility"] / np.sqrt(24)  # Scale to hourly

    data = []
    current_time = start_date
    trend_direction = 0.0
    trend_duration = 0
    trend_max_duration = np.random.randint(20, 60)

    bars_generated = 0
    target_bars = days * 24

    while bars_generated < target_bars:
        # Skip weekends (Saturday=5, Sunday=6)
        if current_time.weekday() >= 5:
            current_time += timedelta(hours=1)
            continue

        # Session-based volatility multiplier
        hour = current_time.hour
        if 7 <= hour <= 16:      # London session
            vol_mult = 1.3
        elif 12 <= hour <= 21:   # NY session (overlap with London = highest)
            vol_mult = 1.4 if hour <= 16 else 1.2
        elif 23 <= hour or hour <= 8:  # Asian session
            vol_mult = 0.6
        else:
            vol_mult = 0.8

        # Trend regime changes
        trend_duration += 1
        if trend_duration >= trend_max_duration:
            trend_direction = np.random.choice([-1, 0, 1], p=[0.35, 0.30, 0.35])
            trend_max_duration = np.random.randint(20, 60)
            trend_duration = 0

        # Price movement: drift + noise
        drift = trend_direction * hourly_vol * 0.15  # Subtle trend
        noise = np.random.normal(0, hourly_vol * vol_mult)
        mean_reversion = -0.001 * (price - params["start_price"])  # Weak pull to mean

        price_change = drift + noise + mean_reversion

        open_price = price
        close_price = price + price_change

        # Generate realistic high/low
        intra_bar_vol = abs(price_change) + hourly_vol * vol_mult * np.random.uniform(0.3, 0.8)
        if close_price > open_price:
            high = close_price + intra_bar_vol * np.random.uniform(0.1, 0.5)
            low = open_price - intra_bar_vol * np.random.uniform(0.1, 0.4)
        else:
            high = open_price + intra_bar_vol * np.random.uniform(0.1, 0.4)
            low = close_price - intra_bar_vol * np.random.uniform(0.1, 0.5)

        # Ensure high >= max(open, close) and low <= min(open, close)
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        volume = int(np.random.exponential(5000) * vol_mult)

        data.append({
            "time": current_time,
            "open": round(open_price, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close_price, 5),
            "volume": volume,
        })

        price = close_price
        current_time += timedelta(hours=1)
        bars_generated += 1

    return pd.DataFrame(data)


def _resample_to_h4(h1_df: pd.DataFrame) -> pd.DataFrame:
    """Resample H1 data to H4 candles.

    Groups every 4 H1 bars into 1 H4 bar using standard OHLC aggregation.

    Args:
        h1_df: H1 OHLC DataFrame.

    Returns:
        H4 OHLC DataFrame.
    """
    df = h1_df.copy()
    df = df.set_index("time")

    h4 = df.resample("4h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna().reset_index()

    return h4


def generate_synthetic(symbol: str, days: int) -> None:
    """Generate synthetic H1 and H4 data and save to CSV."""
    print(f"\n🔧 Generating {days} days of synthetic {symbol} data...")

    h1_df = _generate_h1_data(symbol, days=days)
    h4_df = _resample_to_h4(h1_df)

    # Save to data/
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    h1_path = data_dir / f"{symbol}_H1.csv"
    h4_path = data_dir / f"{symbol}_H4.csv"

    h1_df.to_csv(h1_path, index=False)
    h4_df.to_csv(h4_path, index=False)

    print(f"   ✅ H1: {len(h1_df)} bars → {h1_path}")
    print(f"   ✅ H4: {len(h4_df)} bars → {h4_path}")
    print(f"   📅 Range: {h1_df['time'].iloc[0]} → {h1_df['time'].iloc[-1]}")
    print(f"   💰 Price: {h1_df['close'].iloc[0]:.5f} → {h1_df['close'].iloc[-1]:.5f}")
    print()


# ═══════════════════════════════════════════════════════════════
#  MT5 data download (Windows only)
# ═══════════════════════════════════════════════════════════════

def download_from_mt5(symbol: str, days: int) -> None:
    """Download data from MetaTrader 5 terminal."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("\n❌ MetaTrader5 package not available.")
        print("   MT5 only works on Windows.")
        print("   Use --mode synthetic for testing on macOS.\n")
        sys.exit(1)

    if not mt5.initialize():
        print(f"\n❌ MT5 initialization failed: {mt5.last_error()}")
        print("   Make sure the MT5 terminal is running.\n")
        sys.exit(1)

    from app.core.constants import Timeframe, MT5_TIMEFRAME_MAP

    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    for tf_name, tf_enum in [("H1", Timeframe.H1), ("H4", Timeframe.H4)]:
        mt5_tf = MT5_TIMEFRAME_MAP[tf_enum]
        num_bars = days * (24 if tf_name == "H1" else 6)

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, num_bars)
        if rates is None or len(rates) == 0:
            print(f"❌ No data for {symbol} {tf_name}")
            continue

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]
        df = df.rename(columns={"tick_volume": "volume"})

        path = data_dir / f"{symbol}_{tf_name}.csv"
        df.to_csv(path, index=False)
        print(f"   ✅ {tf_name}: {len(df)} bars → {path}")

    mt5.shutdown()
    print()


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Download/generate OHLC data for backtesting")
    parser.add_argument(
        "--mode", default="synthetic",
        choices=["synthetic", "mt5"],
        help="Data source: 'synthetic' (fake but realistic) or 'mt5' (real, Windows only)",
    )
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--days", type=int, default=500, help="Trading days of data")
    parser.add_argument(
        "--all-symbols", action="store_true",
        help="Generate data for all configured symbols (EURUSD, GBPUSD, XAUUSD)",
    )
    args = parser.parse_args()

    if args.mode == "synthetic":
        if args.all_symbols:
            for sym in SYMBOL_PARAMS:
                generate_synthetic(sym, args.days)
        else:
            generate_synthetic(args.symbol, args.days)

        print("━" * 50)
        print("  ℹ️  This is SYNTHETIC data for testing the pipeline.")
        print("  📈 For real backtesting, you need real market data.")
        print()
        print("  Options for real data:")
        print("    1. MT5 demo account (Windows/VPS)")
        print("       → python scripts/download_data.py --mode mt5")
        print("    2. histdata.com (free CSV downloads)")
        print("       → Download M1 data, resample to H1/H4")
        print("    3. Dukascopy (free tick data)")
        print("       → dukascopy-node or JForex")
        print("━" * 50)

    elif args.mode == "mt5":
        if args.all_symbols:
            for sym in SYMBOL_PARAMS:
                download_from_mt5(sym, args.days)
        else:
            download_from_mt5(args.symbol, args.days)

    print("\n✅ Data ready. Run backtest:")
    print(f"   python scripts/run_backtest.py --symbol {args.symbol}\n")


if __name__ == "__main__":
    main()
