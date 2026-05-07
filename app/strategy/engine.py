"""
Strategy Engine — orchestrates the full analysis pipeline for live execution.

Pipeline (Volatility Breakout System - matched to backtester):
  1. Session filter    → is the current time in active sessions?
  2. Absolute ATR threshold → skip low-vol chop
  3. Squeeze condition → must be compressed for min N bars
  4. Breakout condition → close beyond Donchian channel
  5. Breakout magnitude → candle range >= mult * ATR
  6. H4 Trend Alignment → filter counter-trend breakouts

Output: TradeIdea or None
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import numpy as np

from app.core.config import Settings, get_settings
from app.core.constants import TradeDirection
from app.core.logger import get_logger
from app.models.trade import TradeIdea
from app.utils.math_utils import pips_to_price
from app.utils.time_utils import is_in_session

logger = get_logger("strategy.engine")


class StrategyEngine:
    """Orchestrates the trading strategy analysis pipeline for live trading.
    
    This implementation exactly mirrors app.backtesting.engine.py to ensure
    live trading behaves identically to backtested results.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.strategy_config = self.settings.strategy
        self.symbols_config = self.settings.symbols

    def analyze(
        self,
        h1_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        symbol: str,
        current_time: Optional[datetime] = None,
    ) -> Optional[TradeIdea]:
        """Run the full Volatility Breakout strategy pipeline on closed candle data.

        Args:
            h1_df: H1 OHLC DataFrame (CLOSED candles only).
            h4_df: H4 OHLC DataFrame (CLOSED candles only).
            symbol: Trading symbol (e.g., 'EURUSD').
            current_time: Timestamp of the analysis (for session filtering).

        Returns:
            TradeIdea if all gates pass, None otherwise.
        """
        # ──────────────────────────────────────────────
        # Gate 1: Session filter
        # ──────────────────────────────────────────────
        if current_time is not None:
            if not is_in_session(current_time, self.strategy_config.trading_sessions):
                logger.debug(f"⏭️ Gate 1 (Session) skipped for {symbol} at {current_time} (UTC)")
                return None

        # ──────────────────────────────────────────────
        # Helper: ATR function
        # ──────────────────────────────────────────────
        def _atr(df: pd.DataFrame, period: int) -> pd.Series:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.ewm(alpha=1.0 / period, adjust=False).mean()

        # ──────────────────────────────────────────────
        # Gate 2: Absolute ATR threshold
        # ──────────────────────────────────────────────
        h1_atr_fast = _atr(h1_df, self.strategy_config.squeeze_atr_fast)
        atr = float(h1_atr_fast.iloc[-1])
        if np.isnan(atr) or atr < self.strategy_config.min_atr_threshold:
            logger.debug(f"⏭️ Gate 2 (ATR) skipped for {symbol}: ATR {atr:.5f} < threshold {self.strategy_config.min_atr_threshold}")
            return None

        # ──────────────────────────────────────────────
        # Gate 3: Squeeze condition
        # ──────────────────────────────────────────────
        h1_atr_slow = _atr(h1_df, self.strategy_config.squeeze_atr_slow)
        squeeze_ratio = h1_atr_fast / h1_atr_slow
        is_squeezed = squeeze_ratio < self.strategy_config.squeeze_ratio
        
        # Count consecutive squeezed bars
        squeeze_blocks = (~is_squeezed).cumsum()
        squeeze_consecutive = is_squeezed.groupby(squeeze_blocks).cumsum()
        
        # We check if it was squeezed UP TO the breakout (the bar prior to the breakout close)
        # So we look at the second to last closed candle's squeeze status
        consec_squeezed = int(squeeze_consecutive.iloc[-2]) if len(squeeze_consecutive) > 1 else 0
        if consec_squeezed < self.strategy_config.min_squeeze_bars:
            logger.debug(f"⏭️ Gate 3 (Squeeze) skipped for {symbol}: {consec_squeezed} bars (needed {self.strategy_config.min_squeeze_bars})")
            return None

        # ──────────────────────────────────────────────
        # Gate 4: Breakout condition (Donchian Channel)
        # ──────────────────────────────────────────────
        # Shift(1) so the channel is formed by the PREVIOUS N bars, not including current bar
        h1_donchian_high = h1_df["high"].rolling(window=self.strategy_config.breakout_channel).max().shift(1)
        h1_donchian_low = h1_df["low"].rolling(window=self.strategy_config.breakout_channel).min().shift(1)

        close = float(h1_df["close"].iloc[-1])
        donchian_hi = float(h1_donchian_high.iloc[-1])
        donchian_lo = float(h1_donchian_low.iloc[-1])

        is_long_breakout = close > donchian_hi
        is_short_breakout = close < donchian_lo

        if not is_long_breakout and not is_short_breakout:
            logger.debug(f"⏭️ Gate 4 (Breakout) skipped for {symbol}: Close {close:.5f} within Donchian {donchian_lo:.5f}-{donchian_hi:.5f}")
            return None

        direction = TradeDirection.LONG if is_long_breakout else TradeDirection.SHORT

        # ──────────────────────────────────────────────
        # Gate 5: Breakout Magnitude
        # ──────────────────────────────────────────────
        high = float(h1_df["high"].iloc[-1])
        low = float(h1_df["low"].iloc[-1])
        if (high - low) < (self.strategy_config.min_breakout_atr_mult * atr):
            logger.debug(f"⏭️ Gate 5 (Magnitude) skipped for {symbol}: Range {(high - low):.5f} < {self.strategy_config.min_breakout_atr_mult}*ATR")
            return None

        # ──────────────────────────────────────────────
        # Gate 6: H4 Trend Alignment
        # ──────────────────────────────────────────────
        h4_ema_fast = h4_df["close"].ewm(span=self.strategy_config.ema_fast, adjust=False).mean()
        h4_ema_slow = h4_df["close"].ewm(span=self.strategy_config.ema_slow, adjust=False).mean()
        
        fast = float(h4_ema_fast.iloc[-1])
        slow = float(h4_ema_slow.iloc[-1])

        if direction == TradeDirection.LONG and fast <= slow:
            logger.debug(f"⏭️ Gate 6 (Trend) skipped for {symbol}: Direction LONG but H4 EMA Fast {fast:.5f} <= Slow {slow:.5f}")
            return None
        if direction == TradeDirection.SHORT and fast >= slow:
            logger.debug(f"⏭️ Gate 6 (Trend) skipped for {symbol}: Direction SHORT but H4 EMA Fast {fast:.5f} >= Slow {slow:.5f}")
            return None

        # ──────────────────────────────────────────────
        # Calculate Exit (Fixed TP/SL)
        # ──────────────────────────────────────────────
        min_sl_dist = pips_to_price(
            self.strategy_config.min_sl_pips, symbol, self.symbols_config
        )
        
        sl_dist = max(atr * self.strategy_config.initial_sl_atr, min_sl_dist)
        if direction == TradeDirection.LONG:
            sl = close - sl_dist
            tp = close + (sl_dist * self.strategy_config.rr_ratio)
        else:
            sl = close + sl_dist
            tp = close - (sl_dist * self.strategy_config.rr_ratio)

        rr = self.strategy_config.rr_ratio

        reasoning = {
            "v3_volatility_breakout": True,
            "squeeze_bars": consec_squeezed,
            "breakout_atr_mult": round((high - low) / atr, 2),
        }

        trade_idea = TradeIdea(
            symbol=symbol,
            direction=direction,
            entry_price=close,
            stop_loss=sl,
            take_profit=tp,
            atr=atr,
            risk_reward=rr,
            timestamp=current_time or datetime.utcnow(),
            reasoning=reasoning,
        )

        logger.info(
            f"🟢 Live Volatility Breakout Signal! {symbol} | "
            f"Direction: {direction.value} | "
            f"Entry: {round(close, 5)} | SL: {round(sl, 5)} | TP: {round(tp, 5)}"
        )

        return trade_idea
