"""
Trade Simulator — handles order execution realism in backtesting.

Realism features:
  - Spread applied at entry
  - Slippage (random uniform up to config max)
  - Candle ambiguity via execution_mode:
    - conservative → SL checked first (worst case)
    - optimistic → TP checked first (best case)
    - random → randomly decide (realistic range)
"""

from __future__ import annotations

import random
from datetime import datetime

from app.core.config import Settings, get_settings
from app.core.constants import ExecutionMode, TradeDirection, TradeState
from app.core.logger import get_logger
from app.models.trade import TradeResult
from app.utils.math_utils import pips_to_price, price_to_pips

logger = get_logger("backtesting.simulator")


class TradeSimulator:
    """Simulates realistic trade execution within backtesting.

    Handles spread, slippage, and SL/TP resolution order.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.backtest_config = self.settings.backtest

    def apply_entry_costs(
        self,
        price: float,
        direction: TradeDirection,
        symbol: str,
    ) -> float:
        """Apply spread and slippage to an entry price.

        For LONG: entry = price + spread + slippage (buy at ask)
        For SHORT: entry = price - spread - slippage (sell at bid)

        Slippage is random uniform from 0 to max configured value.

        Args:
            price: Raw entry price (next candle open).
            direction: Trade direction.
            symbol: Trading symbol.

        Returns:
            Adjusted entry price with costs applied.
        """
        symbols_config = self.settings.symbols
        spread = pips_to_price(self.backtest_config.spread_pips, symbol, symbols_config)
        max_slippage = pips_to_price(self.backtest_config.slippage_pips, symbol, symbols_config)
        slippage = random.uniform(0, max_slippage)

        if direction == TradeDirection.LONG:
            adjusted = price + spread + slippage
        else:
            adjusted = price - spread - slippage

        logger.debug(
            f"Entry costs applied: {price:.5f} → {adjusted:.5f} "
            f"(spread={spread:.5f}, slippage={slippage:.5f})",
            symbol=symbol,
        )

        return adjusted

    def check_sl_tp(
        self,
        trade: TradeResult,
        bar_high: float,
        bar_low: float,
        bar_close: float,
        bar_time: datetime,
        symbol: str,
    ) -> Optional[TradeResult]:
        """Check if a bar triggers SL or TP for an open trade.

        Handles candle ambiguity:
        - Both SL and TP could be hit within the same bar
        - execution_mode determines which is checked first

        Trailing Stop Logic:
        - If take_profit is None, uses trailing stop logic.
        - Updates highest_high / lowest_low.
        - Adjusts SL if trailing conditions are met.

        Args:
            trade: The open trade to check.
            bar_high: Current bar's high price.
            bar_low: Current bar's low price.
            bar_close: Current bar's close price.
            bar_time: Current bar's timestamp.
            symbol: Trading symbol.

        Returns:
            Updated TradeResult if trade was closed, None if still open.
        """
        idea = trade.trade_idea
        sl = idea.stop_loss
        tp = idea.take_profit
        entry = idea.entry_price

        # ── 1. Update Excursions (for trailing stops) ──
        if trade.highest_high is None or bar_high > trade.highest_high:
            trade.highest_high = bar_high
        if trade.lowest_low is None or bar_low < trade.lowest_low:
            trade.lowest_low = bar_low

        # ── 2. Handle Trailing Stop Adjustment ──
        if tp is None:
            cfg = self.settings.strategy
            atr = idea.atr

            if idea.direction == TradeDirection.LONG:
                # Breakeven check
                if trade.highest_high >= entry + (atr * cfg.breakeven_atr):
                    if sl < entry:
                        sl = entry
                        idea.stop_loss = sl
                # Trailing check
                trail_level = trade.highest_high - (atr * cfg.trail_atr)
                if trail_level > sl:
                    sl = trail_level
                    idea.stop_loss = sl
            else:
                # Breakeven check
                if trade.lowest_low <= entry - (atr * cfg.breakeven_atr):
                    if sl > entry:
                        sl = entry
                        idea.stop_loss = sl
                # Trailing check
                trail_level = trade.lowest_low + (atr * cfg.trail_atr)
                if trail_level < sl:
                    sl = trail_level
                    idea.stop_loss = sl

        # ── 3. Check for Hits ──
        if idea.direction == TradeDirection.LONG:
            sl_hit = bar_low <= sl
            tp_hit = tp is not None and bar_high >= tp
        else:
            sl_hit = bar_high >= sl
            tp_hit = tp is not None and bar_low <= tp

        # Neither hit — trade stays open
        if not sl_hit and not tp_hit:
            return None

        # Resolve ambiguity if both are hit
        if sl_hit and tp_hit:
            mode = ExecutionMode(self.backtest_config.execution_mode)
            if mode == ExecutionMode.CONSERVATIVE:
                # Worst case: SL hit first
                return self._close_trade(trade, sl, TradeState.STOPPED, bar_time, symbol)
            elif mode == ExecutionMode.OPTIMISTIC:
                # Best case: TP hit first
                return self._close_trade(trade, tp, TradeState.TARGET_HIT, bar_time, symbol)
            else:
                # Random: 50/50 weighted
                if random.random() < 0.5:
                    return self._close_trade(trade, sl, TradeState.STOPPED, bar_time, symbol)
                else:
                    return self._close_trade(trade, tp, TradeState.TARGET_HIT, bar_time, symbol)

        # Only one was hit
        if sl_hit:
            return self._close_trade(trade, sl, TradeState.STOPPED, bar_time, symbol)
        else:
            return self._close_trade(trade, tp, TradeState.TARGET_HIT, bar_time, symbol)

    def _close_trade(
        self,
        trade: TradeResult,
        exit_price: float,
        state: TradeState,
        exit_time: datetime,
        symbol: str,
    ) -> TradeResult:
        """Close a trade and calculate PnL.

        Args:
            trade: The trade to close.
            exit_price: Price at which the trade exits.
            state: Terminal state (STOPPED or TARGET_HIT).
            exit_time: Timestamp of the exit.
            symbol: Trading symbol.

        Returns:
            Updated TradeResult with PnL calculated.
        """
        idea = trade.trade_idea
        entry = idea.entry_price

        # Calculate PnL in pips
        if idea.direction == TradeDirection.LONG:
            pnl_raw = exit_price - entry
        else:
            pnl_raw = entry - exit_price

        pnl_pips = price_to_pips(abs(pnl_raw), symbol, self.settings.symbols)
        if pnl_raw < 0:
            pnl_pips = -pnl_pips

        # Convert to dollar PnL (using 1 lot equivalent for backtesting)
        # pip_value for 1 lot * pnl_pips
        from app.utils.math_utils import get_pip_value
        pip_value = get_pip_value(symbol, 1.0, self.settings.symbols)
        pnl_dollars = pnl_pips * pip_value

        trade.state = state
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.pnl = pnl_dollars
        trade.pnl_pips = pnl_pips

        logger.debug(
            f"Trade closed: {state.value}, PnL: {pnl_pips:.1f} pips (${pnl_dollars:.2f})",
            symbol=symbol,
            entry=round(entry, 5),
            exit=round(exit_price, 5),
        )

        return trade
