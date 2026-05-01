"""
resample_m1.py — Convert M1 (1-minute) data into H1 and H4 candles.

Supports common M1 CSV formats:
  - histdata.com: no header, semicolon-separated (DATE;TIME;OPEN;HIGH;LOW;CLOSE;VOLUME)
  - Standard: time,open,high,low,close,volume
  - MT5 export: date,time,open,high,low,close,tickvol,vol,spread

Auto-detects format and resamples with proper OHLC aggregation:
  - open  → first
  - high  → max
  - low   → min
  - close → last
  - volume → sum

Usage:
    python scripts/resample_m1.py data/EURUSD_M1.csv --symbol EURUSD
    python scripts/resample_m1.py data/EURUSD_M1.csv --symbol EURUSD --timeframes H1 H4 D1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))


# Resample rules for OHLCV
OHLCV_AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}

# Timeframe → pandas resample frequency
TF_MAP = {
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
    "W1": "1W",
}


def detect_and_load(filepath: str) -> pd.DataFrame:
    """Auto-detect CSV format and load M1 data into a standardized DataFrame.

    Handles:
    - histdata.com format (semicolons, no header, YYYYMMDD HHMMSS)
    - Standard CSV (time,open,high,low,close,volume)
    - MT5 export format
    - Various date formats

    Returns:
        DataFrame with columns: time, open, high, low, close, volume
    """
    path = Path(filepath)
    if not path.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    # Peek at the first few lines to detect format
    with open(path, "r") as f:
        first_lines = [f.readline() for _ in range(5)]

    sample = first_lines[0]

    # ── histdata.com format (semicolons, no header) ──
    if ";" in sample and not sample.lower().startswith(("date", "time", "open")):
        print("   Format detected: histdata.com (semicolon-separated)")
        df = pd.read_csv(
            path, sep=";", header=None,
            names=["date", "time_str", "open", "high", "low", "close", "volume"],
            dtype={"date": str, "time_str": str},
        )
        # histdata date formats: YYYYMMDD or YYYY.MM.DD
        if "." in str(df["date"].iloc[0]):
            df["time"] = pd.to_datetime(
                df["date"] + " " + df["time_str"], format="%Y.%m.%d %H:%M:%S"
            )
        else:
            df["time"] = pd.to_datetime(
                df["date"] + " " + df["time_str"], format="%Y%m%d %H%M%S"
            )
        df = df[["time", "open", "high", "low", "close", "volume"]]

    # ── Tab-separated (MT5 exports: <DATE> <TIME> <OPEN> ... <TICKVOL> <VOL> <SPREAD>) ──
    elif "\t" in sample:
        print("   Format detected: MT5 tab-separated export")
        df = pd.read_csv(path, sep="\t")
        # Strip angle brackets and lowercase: <DATE> → date, <TICKVOL> → tickvol
        df.columns = [c.lower().strip().strip("<>") for c in df.columns]

        # Combine date + time into a single datetime column
        if "date" in df.columns and "time" in df.columns:
            df["time"] = pd.to_datetime(df["date"] + " " + df["time"])
            df = df.drop(columns=["date"])
        elif "date" in df.columns:
            df["time"] = pd.to_datetime(df["date"])
            df = df.drop(columns=["date"])

        # Use tickvol as volume (tick volume is what matters for forex)
        if "tickvol" in df.columns:
            df["volume"] = df["tickvol"]

        # Drop extra MT5 columns
        df = df.drop(columns=[c for c in ["tickvol", "vol", "spread"] if c in df.columns], errors="ignore")

        # Keep only what we need
        df = df[["time", "open", "high", "low", "close", "volume"]]

    # ── Standard comma-separated CSV ──
    else:
        print("   Format detected: standard CSV")
        # Check if first line is a header
        has_header = any(
            keyword in sample.lower()
            for keyword in ["time", "date", "open", "high", "close"]
        )
        if has_header:
            df = pd.read_csv(path)
        else:
            df = pd.read_csv(
                path, header=None,
                names=["time", "open", "high", "low", "close", "volume"],
            )
        df.columns = [c.lower().strip() for c in df.columns]
        df = _standardize_columns(df)

    # Ensure time is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["time"]):
        df["time"] = pd.to_datetime(df["time"], utc=True)

    # Ensure numeric columns
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 0
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

    # ── Detect and strip embedded daily bars ──
    # MT5 exports sometimes prepend D1 bars before the actual M1 data.
    # Daily bars have: midnight-only timestamps + abnormally high tick volume.
    # Real M1 bars have varied times (00:01, 00:02, etc.) and low tick volume (<500).
    time_col = df["time"]
    is_midnight = (time_col.dt.hour == 0) & (time_col.dt.minute == 0) & (time_col.dt.second == 0)

    # Find where the first non-midnight bar appears
    non_midnight_mask = ~is_midnight
    if non_midnight_mask.any():
        first_m1_idx = non_midnight_mask.idxmax()
        if first_m1_idx > 0:
            n_daily = first_m1_idx
            print(f"   ⚠️  Detected {n_daily} embedded daily bars at file start — stripping them")
            df = df.iloc[first_m1_idx:].reset_index(drop=True)

    # Sort by time and drop duplicates
    df = df.sort_values("time").drop_duplicates(subset=["time"]).reset_index(drop=True)

    # Drop NaN prices
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    return df[["time", "open", "high", "low", "close", "volume"]]


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map common column name variants to standard names."""
    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ("datetime", "date_time", "timestamp", "<date>"):
            col_map[col] = "time"
        elif cl in ("<time>",) and "time" not in df.columns:
            col_map[col] = "time_part"
        elif cl in ("<open>",):
            col_map[col] = "open"
        elif cl in ("<high>",):
            col_map[col] = "high"
        elif cl in ("<low>",):
            col_map[col] = "low"
        elif cl in ("<close>",):
            col_map[col] = "close"
        elif cl in ("tick_volume", "tickvol", "<tickvol>", "<vol>"):
            col_map[col] = "volume"

    if col_map:
        df = df.rename(columns=col_map)

    # Combine date + time columns if separate
    if "date" in df.columns and "time_part" in df.columns:
        df["time"] = pd.to_datetime(df["date"].astype(str) + " " + df["time_part"].astype(str))
    elif "date" in df.columns and "time" not in df.columns:
        df["time"] = pd.to_datetime(df["date"])

    return df


def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample M1 data to a higher timeframe.

    Args:
        df: M1 DataFrame with time, open, high, low, close, volume.
        timeframe: Target timeframe (H1, H4, D1, etc.).

    Returns:
        Resampled OHLCV DataFrame.
    """
    freq = TF_MAP.get(timeframe)
    if freq is None:
        print(f"❌ Unsupported timeframe: {timeframe}. Options: {list(TF_MAP.keys())}")
        sys.exit(1)

    resampled = (
        df.set_index("time")
        .resample(freq)
        .agg(OHLCV_AGG)
        .dropna()
        .reset_index()
    )

    return resampled


def main():
    parser = argparse.ArgumentParser(description="Resample M1 data to H1/H4")
    parser.add_argument("file", help="Path to M1 CSV file")
    parser.add_argument("--symbol", required=True, help="Symbol name (e.g., EURUSD)")
    parser.add_argument(
        "--timeframes", nargs="+", default=["H1", "H4"],
        help="Target timeframes (default: H1 H4)",
    )
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 Loading M1 data from: {args.file}")
    m1_df = detect_and_load(args.file)
    print(f"   ✅ Loaded {len(m1_df):,} M1 bars")
    print(f"   📅 Range: {m1_df['time'].iloc[0]} → {m1_df['time'].iloc[-1]}")
    print(f"   💰 Price: {m1_df['close'].iloc[0]:.5f} → {m1_df['close'].iloc[-1]:.5f}")
    print()

    for tf in args.timeframes:
        resampled = resample(m1_df, tf)
        filepath = output_dir / f"{args.symbol}_{tf}.csv"
        resampled.to_csv(filepath, index=False)
        print(f"   ✅ {tf}: {len(resampled):,} bars → {filepath}")

    print(f"\n✅ Done. Run backtest:")
    print(f"   python scripts/run_backtest.py --symbol {args.symbol}\n")


if __name__ == "__main__":
    main()
