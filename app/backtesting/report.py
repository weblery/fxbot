"""
Backtest report — console summary + equity curve + trade log CSV.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.backtesting.engine import BacktestResult
from app.backtesting.metrics import calculate_metrics, BacktestMetrics
from app.core.logger import get_logger

logger = get_logger("backtesting.report")


def generate_report(
    result: BacktestResult,
    min_trades: int = 100,
    output_dir: str | Path | None = None,
) -> BacktestMetrics:
    """Generate a backtest report with console output and saved files.

    Args:
        result: BacktestResult from the backtest engine.
        min_trades: Minimum trades for statistical validity.
        output_dir: Directory for output files. Defaults to reports/.

    Returns:
        Calculated BacktestMetrics.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "reports"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = calculate_metrics(result.trades, result.equity_curve, min_trades)

    # Console report
    _print_summary(result, metrics)

    # Save equity curve
    if result.equity_curve:
        _save_equity_curve(result, output_dir)

    # Save trade log
    if result.trades:
        _save_trade_log(result, output_dir)

    return metrics


def _print_summary(result: BacktestResult, m: BacktestMetrics) -> None:
    print("\n" + "═" * 55)
    print(f"  FOREXBOT Backtest Report — {result.symbol}")
    print("═" * 55)
    print(f"  Mode:            {result.execution_mode}")
    print(f"  Total Trades:    {m.total_trades}")
    print(f"  Win Rate:        {m.win_rate:.1%}")
    print(f"  Profit Factor:   {m.profit_factor:.2f}")
    print(f"  Expectancy:      ${m.expectancy:.2f} per trade")
    print(f"  Avg Win:         ${m.avg_win:.2f}")
    print(f"  Avg Loss:        ${m.avg_loss:.2f}")
    print(f"  Largest Win:     ${m.largest_win:.2f}")
    print(f"  Largest Loss:    ${m.largest_loss:.2f}")
    print(f"  Avg PnL (pips):  {m.avg_pnl_pips:.1f}")
    print(f"  Max Drawdown:    {m.max_drawdown_pct:.1%} (${m.max_drawdown_amount:.2f})")
    print(f"  Sharpe Ratio:    {m.sharpe_ratio:.2f}")
    print(f"  Total PnL:       ${m.total_pnl:.2f}")
    print(f"  Final Balance:   ${result.final_balance:.2f}")
    print()
    if not m.min_trades_met:
        print(f"  ⚠️  Min trades NOT met ({m.total_trades} < 100)")
        print(f"      Results may not be statistically significant!")
    else:
        print(f"  ✅ Min trades met ({m.total_trades} ≥ 100)")
    print("═" * 55 + "\n")


def _save_equity_curve(result: BacktestResult, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(result.equity_curve, linewidth=1.2, color="#2196F3")
    ax.axhline(y=result.initial_balance, color="#888", linestyle="--", alpha=0.5)
    ax.set_title(f"Equity Curve — {result.symbol} ({result.execution_mode})")
    ax.set_xlabel("Bar")
    ax.set_ylabel("Balance ($)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = output_dir / f"equity_{result.symbol}_{result.execution_mode}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Equity curve saved to {path}")


def _save_trade_log(result: BacktestResult, output_dir: Path) -> None:
    path = output_dir / f"trades_{result.symbol}_{result.execution_mode}.csv"
    with open(path, "w") as f:
        f.write("symbol,direction,entry,sl,tp,exit,state,pnl,pnl_pips,time\n")
        for t in result.trades:
            i = t.trade_idea
            tp_str = f"{i.take_profit:.5f}" if i.take_profit is not None else "Trailing"
            exit_str = f"{t.exit_price:.5f}" if t.exit_price is not None else ""
            pnl_str = f"{t.pnl:.2f}" if t.pnl is not None else ""
            pips_str = f"{t.pnl_pips:.1f}" if t.pnl_pips is not None else ""
            f.write(
                f"{i.symbol},{i.direction.value},{i.entry_price:.5f},"
                f"{i.stop_loss:.5f},{tp_str},"
                f"{exit_str},{t.state.value},{pnl_str},"
                f"{pips_str},{t.exit_time}\n"
            )
    logger.info(f"Trade log saved to {path}")
