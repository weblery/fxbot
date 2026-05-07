"""
Backtest Engine — runs the strategy on historical data bar-by-bar.

PERFORMANCE: Pre-calculates all indicators once on the full dataset.
This is mathematically equivalent to incremental calculation because EMAs
and ATR are causal filters (they only look backwards). Reading the
pre-calculated value at index i-1 is identical to computing on df.iloc[:i].

CRITICAL INTEGRITY RULES:
  1. NO DATA LEAKAGE: Reads indicators at index i-1 (only closed candles)
  2. ENTRY ON NEXT OPEN: Signal at bar i → entry at bar i+1 open
  3. SINGLE POSITION: Only one trade per symbol at a time
  4. MULTI-TIMEFRAME: H4 trend synced by timestamp, H1 for execution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from app.core.config import Settings, get_settings
from app.core.constants import TradeDirection, TradeState
from app.core.logger import get_logger
from app.models.trade import TradeIdea, TradeResult
from app.backtesting.simulator import TradeSimulator
from app.strategy.exit import calculate_stop_loss, calculate_take_profit
from app.utils.math_utils import pips_to_price
from app.utils.time_utils import is_in_session

logger = get_logger("backtesting.engine")


@dataclass
class BacktestResult:
    """Complete results from a backtest run."""
    trades: list[TradeResult] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    initial_balance: float = 10000.0
    final_balance: float = 10000.0
    symbol: str = ""
    execution_mode: str = "conservative"


def _ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate EMA using pandas (causal — only looks backwards)."""
    return series.ewm(span=period, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate ATR series using Wilder's smoothing."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


class BacktestEngine:
    """Runs the strategy on historical data with pre-calculated indicators.

    All indicators are computed once on the full dataset. The bar-by-bar loop
    only reads pre-computed values at index i-1 (closed candles). This is
    1000x faster than recomputing EMAs on every iteration.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.simulator = TradeSimulator(self.settings)

    def run(
        self,
        h1_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        symbol: str,
    ) -> BacktestResult:
        """Run a full backtest on historical data.

        Args:
            h1_df: H1 OHLC data (full historical dataset).
            h4_df: H4 OHLC data (full historical dataset).
            symbol: Trading symbol.

        Returns:
            BacktestResult with all trades, equity curve, and timestamps.
        """
        cfg = self.settings.strategy
        bt_cfg = self.settings.backtest
        balance = bt_cfg.initial_balance

        result = BacktestResult(
            initial_balance=balance,
            symbol=symbol,
            execution_mode=bt_cfg.execution_mode,
        )

        # ──────────────────────────────────────────
        # Phase 1: Pre-calculate ALL indicators
        # ──────────────────────────────────────────
        logger.info(f"Pre-calculating indicators for {symbol}...")

        # H4 trend indicators
        h4_ema_fast = _ema(h4_df["close"], cfg.ema_fast)
        h4_ema_slow = _ema(h4_df["close"], cfg.ema_slow)

        # H1 execution indicators (Volatility Breakout v3)
        h1_atr_fast = _atr(h1_df, cfg.squeeze_atr_fast)
        h1_atr_slow = _atr(h1_df, cfg.squeeze_atr_slow)
        
        # Donchian Channels
        h1_donchian_high = h1_df["high"].rolling(window=cfg.breakout_channel).max().shift(1)
        h1_donchian_low = h1_df["low"].rolling(window=cfg.breakout_channel).min().shift(1)
        
        # Volatility Squeeze Ratio
        squeeze_ratio = h1_atr_fast / h1_atr_slow
        is_squeezed = squeeze_ratio < cfg.squeeze_ratio
        
        # Count consecutive squeezed bars
        # This creates a cumulative sum that resets to 0 when not squeezed
        squeeze_blocks = (~is_squeezed).cumsum()
        squeeze_consecutive = is_squeezed.groupby(squeeze_blocks).cumsum()

        # Build H4 time index for fast timestamp lookup (as int64 for searchsorted)
        h4_times = pd.to_datetime(h4_df["time"]).values.astype(np.int64)

        # Min SL in price units
        min_sl_dist = pips_to_price(cfg.min_sl_pips, symbol, self.settings.symbols)

        # Minimum lookback
        min_h1 = max(cfg.ema_slow, 200) + 50
        min_h4 = cfg.ema_slow + 10

        if len(h1_df) < min_h1:
            logger.error(f"Insufficient H1 data: {len(h1_df)} bars, need {min_h1}")
            return result

        # ──────────────────────────────────────────
        # Phase 2: Bar-by-bar execution
        # ──────────────────────────────────────────
        open_trade: Optional[TradeResult] = None
        pending_signal: Optional[TradeIdea] = None
        cooldown_remaining: int = 0  # v2: trade cooldown counter

        logger.info(
            f"Starting backtest: {symbol}, {len(h1_df)} H1 bars, "
            f"mode={bt_cfg.execution_mode}"
        )

        for i in range(min_h1, len(h1_df)):
            bar = h1_df.iloc[i]
            bar_time = bar["time"]
            bar_open = float(bar["open"])
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])
            bar_close = float(bar["close"])

            # ── Step 1: Execute pending signal on this bar's open ──
            if pending_signal is not None and open_trade is None:
                entry_price = self.simulator.apply_entry_costs(
                    price=bar_open,
                    direction=pending_signal.direction,
                    symbol=symbol,
                )

                sl_dist = pending_signal.sl_distance
                if pending_signal.direction == TradeDirection.LONG:
                    actual_sl = entry_price - sl_dist
                    actual_tp = entry_price + (sl_dist * cfg.rr_ratio)
                else:
                    actual_sl = entry_price + sl_dist
                    actual_tp = entry_price - (sl_dist * cfg.rr_ratio)

                actual_idea = TradeIdea(
                    symbol=symbol,
                    direction=pending_signal.direction,
                    entry_price=entry_price,
                    stop_loss=actual_sl,
                    take_profit=actual_tp,
                    atr=pending_signal.atr,
                    risk_reward=pending_signal.risk_reward,
                    timestamp=bar_time,
                    reasoning=pending_signal.reasoning,
                )

                open_trade = TradeResult(trade_idea=actual_idea, state=TradeState.OPEN)
                pending_signal = None

            # ── Step 2: Check SL/TP on current bar ──
            if open_trade is not None and open_trade.state == TradeState.OPEN:
                closed = self.simulator.check_sl_tp(
                    trade=open_trade,
                    bar_high=bar_high,
                    bar_low=bar_low,
                    bar_close=bar_close,
                    bar_time=bar_time,
                    symbol=symbol,
                )
                if closed is not None:
                    balance += closed.pnl or 0
                    result.trades.append(closed)
                    open_trade = None
                    cooldown_remaining = cfg.min_bars_between_trades  # v2: start cooldown

            # ── Step 3: Record equity ──
            result.equity_curve.append(balance)
            result.timestamps.append(bar_time)

            # ── Step 4: Generate signal (only if flat + cooldown expired) ──
            if cooldown_remaining > 0:
                cooldown_remaining -= 1
                continue

            if open_trade is None and pending_signal is None:
                signal = self._check_signal(
                    i=i - 1,  # Use CLOSED candle (i-1), NOT current bar
                    h1_df=h1_df,
                    h1_atr_fast=h1_atr_fast,
                    h1_atr_slow=h1_atr_slow,
                    h1_donchian_high=h1_donchian_high,
                    h1_donchian_low=h1_donchian_low,
                    squeeze_consecutive=squeeze_consecutive,
                    h4_ema_fast=h4_ema_fast,
                    h4_ema_slow=h4_ema_slow,
                    h4_times=h4_times,
                    bar_time=bar_time,
                    symbol=symbol,
                    cfg=cfg,
                    min_sl_dist=min_sl_dist,
                    min_h4=min_h4,
                )
                if signal is not None:
                    pending_signal = signal

        # Close any remaining open trade
        if open_trade is not None and open_trade.state == TradeState.OPEN:
            last = h1_df.iloc[-1]
            open_trade.state = TradeState.CLOSED
            open_trade.exit_price = float(last["close"])
            open_trade.exit_time = last["time"]
            entry = open_trade.trade_idea.entry_price
            d = open_trade.trade_idea.direction
            if d == TradeDirection.LONG:
                open_trade.pnl = (open_trade.exit_price - entry) * self._lot_value(symbol)
            else:
                open_trade.pnl = (entry - open_trade.exit_price) * self._lot_value(symbol)
            balance += open_trade.pnl or 0
            result.trades.append(open_trade)

        result.final_balance = balance

        logger.info(
            f"Backtest complete: {len(result.trades)} trades, "
            f"${result.initial_balance:.2f} → ${result.final_balance:.2f}"
        )
        return result

    def _check_signal(
        self,
        i: int,
        h1_df: pd.DataFrame,
        h1_atr_fast: pd.Series,
        h1_atr_slow: pd.Series,
        h1_donchian_high: pd.Series,
        h1_donchian_low: pd.Series,
        squeeze_consecutive: pd.Series,
        h4_ema_fast: pd.Series,
        h4_ema_slow: pd.Series,
        h4_times,
        bar_time,
        symbol: str,
        cfg,
        min_sl_dist: float,
        min_h4: int,
    ) -> Optional[TradeIdea]:
        """Check for a trade signal using pre-calculated indicators.

        v3 gates (Volatility Breakout System):
          1. Session filter
          2. Absolute ATR threshold (must be moving)
          3. Squeeze condition (must be compressed for N bars)
          4. Breakout condition (close beyond Donchian channel)
          5. Breakout magnitude (candle range >= 0.5 ATR)
          6. H4 trend alignment (filter counter-trend breakouts)

        Reads values at index i (the last CLOSED candle). No data leakage.
        """
        # Gate 1: Session filter
        if hasattr(bar_time, 'hour'):
            if not is_in_session(bar_time, cfg.trading_sessions):
                return None

        # Gate 2: Absolute ATR threshold
        atr = float(h1_atr_fast.iloc[i])
        if np.isnan(atr) or atr < cfg.min_atr_threshold:
            return None

        # Gate 3: Squeeze condition
        # Market must be compressed for at least min_squeeze_bars prior to this bar
        consec_squeezed = int(squeeze_consecutive.iloc[i-1])
        if consec_squeezed < cfg.min_squeeze_bars:
            return None

        # Gate 4: Breakout condition
        close = float(h1_df["close"].iloc[i])
        donchian_hi = float(h1_donchian_high.iloc[i])
        donchian_lo = float(h1_donchian_low.iloc[i])

        is_long_breakout = close > donchian_hi
        is_short_breakout = close < donchian_lo

        if not is_long_breakout and not is_short_breakout:
            return None

        direction = TradeDirection.LONG if is_long_breakout else TradeDirection.SHORT

        # Gate 5: Breakout Magnitude
        # Real breakouts have momentum, not just wicks
        high = float(h1_df["high"].iloc[i])
        low = float(h1_df["low"].iloc[i])
        if (high - low) < (cfg.min_breakout_atr_mult * atr):
            return None

        # Gate 6: H4 Trend Alignment
        bar_time_int = np.int64(pd.Timestamp(bar_time).value)
        h4_idx = np.searchsorted(h4_times, bar_time_int, side="right") - 1
        if h4_idx < min_h4:
            return None

        fast = float(h4_ema_fast.iloc[h4_idx])
        slow = float(h4_ema_slow.iloc[h4_idx])

        # Filter out counter-trend breakouts
        if direction == TradeDirection.LONG and fast <= slow:
            return None
        if direction == TradeDirection.SHORT and fast >= slow:
            return None

        # Calculate Exit (Fixed TP/SL)
        # Initial SL is based on ATR
        sl_dist = max(atr * cfg.initial_sl_atr, min_sl_dist)
        if direction == TradeDirection.LONG:
            sl = close - sl_dist
            tp = close + (sl_dist * cfg.rr_ratio)
        else:
            sl = close + sl_dist
            tp = close - (sl_dist * cfg.rr_ratio)

        return TradeIdea(
            symbol=symbol,
            direction=direction,
            entry_price=close,
            stop_loss=sl,
            take_profit=tp,
            atr=atr,
            risk_reward=cfg.rr_ratio,
            timestamp=bar_time,
            reasoning={
                "v3": True,
                "squeeze_bars": consec_squeezed,
                "breakout_atr_mult": round((high - low) / atr, 2),
            },
        )

    def _lot_value(self, symbol: str) -> float:
        """
        Calculates the dollar value of 1 PIP for 1 standard lot.
        For USD-denominated accounts:
        - EURUSD (0.0001) -> $10.00
        - USDJPY (0.01)   -> ~$6.50 (Simplified to $10 for backtest consistency, or use close price)
        """
        config = self.settings.symbols.get(symbol)
        if not config:
            return 10.0
            
        # Standardize: 1 lot pip value = Contract Size * Pip Size
        # For EURUSD: 100,000 * 0.0001 = $10
        # For USDJPY: 100,000 * 0.01 = 1,000 JPY
        val = config.contract_size * config.pip_size
        
        # If it's a JPY pair, we must convert JPY to USD (roughly divide by 100-150)
        # For a backtest, we use a fixed normalization to keep it comparable
        if "JPY" in symbol:
            return val / 150.0  # Approx exchange rate for realistic USD PnL
            
        return val
