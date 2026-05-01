"""
run_backtest.py — The critical first test.

Loads CSV data → runs strategy + backtest across all 3 execution modes →
prints comparison table → saves equity curves.

Usage:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --symbol EURUSD --mode conservative
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import load_settings
from app.core.logger import setup_logging, get_logger
from app.backtesting.engine import BacktestEngine
from app.backtesting.report import generate_report
from app.backtesting.metrics import calculate_metrics
from app.data.storage import DataStorage
from app.data.transformer import transform_raw_data

logger = get_logger("scripts.run_backtest")


def main():
    parser = argparse.ArgumentParser(description="FOREXBOT Backtester")
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--config", default=None, help="Config file path")
    parser.add_argument(
        "--mode",
        default="all",
        choices=["conservative", "optimistic", "random", "all"],
        help="Execution mode (or 'all' to compare)",
    )
    args = parser.parse_args()

    # Load config
    settings = load_settings(args.config)
    setup_logging(settings.logging.level, settings.logging.format)

    logger.info(f"Starting backtest for {args.symbol}")

    # Load data
    storage = DataStorage()
    h1_df = storage.load(args.symbol, "H1")
    h4_df = storage.load(args.symbol, "H4")

    if h1_df.empty or h4_df.empty:
        print(f"\n❌ No data found for {args.symbol}.")
        print(f"   Place CSV files at:")
        print(f"     data/{args.symbol}_H1.csv")
        print(f"     data/{args.symbol}_H4.csv")
        print(f"\n   Required columns: time, open, high, low, close, volume\n")
        sys.exit(1)

    print(f"\n📊 Loaded {len(h1_df)} H1 bars and {len(h4_df)} H4 bars for {args.symbol}\n")

    # Run backtest(s)
    if args.mode == "all":
        modes = ["conservative", "optimistic", "random"]
    else:
        modes = [args.mode]

    results = {}
    for mode in modes:
        settings.backtest.execution_mode = mode
        engine = BacktestEngine(settings)
        result = engine.run(h1_df, h4_df, args.symbol)
        metrics = generate_report(result, min_trades=settings.backtest.min_trades)
        results[mode] = (result, metrics)

    # Print comparison table if running all modes
    if len(results) > 1:
        print("\n" + "═" * 70)
        print("  EXECUTION MODE COMPARISON")
        print("═" * 70)
        header = f"  {'Metric':<22} {'Conservative':>14} {'Optimistic':>14} {'Random':>14}"
        print(header)
        print("  " + "─" * 66)

        for key, fmt in [
            ("total_trades", "{:.0f}"),
            ("win_rate", "{:.1%}"),
            ("profit_factor", "{:.2f}"),
            ("expectancy", "${:.2f}"),
            ("max_drawdown_pct", "{:.1%}"),
            ("sharpe_ratio", "{:.2f}"),
            ("total_pnl", "${:.2f}"),
        ]:
            vals = []
            for mode in modes:
                v = getattr(results[mode][1], key)
                vals.append(fmt.format(v))
            label = key.replace("_", " ").title()
            print(f"  {label:<22} {vals[0]:>14} {vals[1]:>14} {vals[2]:>14}")

        print("═" * 70)

        # Interpretation
        con = results["conservative"][1]
        rand = results["random"][1]
        opt = results["optimistic"][1]

        print("\n  📋 INTERPRETATION:")
        if con.expectancy > 0:
            print("  ✅ Conservative mode profitable → STRONG strategy")
        elif rand.expectancy > 0:
            print("  ⚠️  Only random/optimistic profitable → FRAGILE strategy")
        elif opt.expectancy > 0:
            print("  ❌ Only optimistic profitable → TRASH — don't trade this")
        else:
            print("  ❌ Not profitable in any mode — strategy needs rework")

        if con.max_drawdown_pct < 0.25:
            print(f"  ✅ Max drawdown {con.max_drawdown_pct:.1%} < 25% threshold")
        else:
            print(f"  ⚠️  Max drawdown {con.max_drawdown_pct:.1%} exceeds 25% — risky")
        print()


if __name__ == "__main__":
    main()
