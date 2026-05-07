"""
Backtest metrics — calculates performance statistics from trade results.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from app.core.constants import TradeState
from app.core.logger import get_logger
from app.models.trade import TradeResult

logger = get_logger("backtesting.metrics")


@dataclass
class BacktestMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_amount: float = 0.0
    sharpe_ratio: float = 0.0
    total_pnl: float = 0.0
    avg_rr_achieved: float = 0.0
    avg_pnl_pips: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    min_trades_met: bool = True


def calculate_metrics(
    trades: list[TradeResult],
    equity_curve: Optional[list[float]] = None,
    min_trades: int = 100,
) -> BacktestMetrics:
    m = BacktestMetrics()
    closed = [t for t in trades if t.is_closed and t.pnl is not None]
    m.total_trades = len(closed)

    if m.total_trades == 0:
        return m

    m.min_trades_met = m.total_trades >= min_trades
    if not m.min_trades_met:
        logger.warning(f"Only {m.total_trades} trades — below minimum {min_trades}")

    winners = [t for t in closed if t.pnl > 0]
    losers = [t for t in closed if t.pnl <= 0]
    m.winning_trades = len(winners)
    m.losing_trades = len(losers)
    m.win_rate = m.winning_trades / m.total_trades

    if winners:
        wpnl = [t.pnl for t in winners]
        m.avg_win = float(np.mean(wpnl))
        m.largest_win = max(wpnl)
    if losers:
        lpnl = [abs(t.pnl) for t in losers]
        m.avg_loss = float(np.mean(lpnl))
        m.largest_loss = max(lpnl)

    gp = sum(t.pnl for t in winners)
    gl = abs(sum(t.pnl for t in losers))
    m.profit_factor = gp / gl if gl > 0 else float("inf")
    m.expectancy = (m.win_rate * m.avg_win) - ((1 - m.win_rate) * m.avg_loss)
    m.total_pnl = sum(t.pnl for t in closed)

    pips = [t.pnl_pips for t in closed if t.pnl_pips is not None]
    m.avg_pnl_pips = float(np.mean(pips)) if pips else 0.0

    if equity_curve and len(equity_curve) > 1:
        curve = np.array(equity_curve)
        peak = np.maximum.accumulate(curve)
        dd = (peak - curve) / peak
        m.max_drawdown_pct = float(np.max(dd))
        m.max_drawdown_amount = float(np.max(peak - curve))

    pnl_series = [t.pnl for t in closed]
    if len(pnl_series) > 1:
        r = np.array(pnl_series)
        std = np.std(r, ddof=1)
        if std > 0:
            m.sharpe_ratio = float((np.mean(r) / std) * np.sqrt(252))

    return m
