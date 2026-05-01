"""
Strategy Engine — orchestrates the full analysis pipeline.

Pipeline (each step is a gate — fails early if any step returns None/False):
  1. Session filter    → is the current time in LONDON or NEW_YORK?
  2. ATR threshold     → is volatility above minimum? (skip chop)
  3. Trend detection   → EMA(50) vs EMA(200) on H4
  4. Pullback check    → price touched EMA(20) on H1
  5. Entry confirmation → candle body ratio + direction alignment
  6. Exit calculation  → ATR-based SL (with floor) + RR-based TP

Output: TradeIdea or None

CRITICAL RULES:
  - Uses CLOSED candles only (no data leakage)
  - Entry price is the signal candle's close (backtest uses next open)
  - H4 trend data and H1 execution data are explicitly separated
  - Every decision step is logged to the reasoning dict
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.core.config import Settings, get_settings
from app.core.constants import TradeDirection
from app.core.logger import get_logger
from app.models.trade import TradeIdea
from app.strategy.trend import detect_trend
from app.strategy.pullback import detect_pullback
from app.strategy.atr import calculate_atr
from app.strategy.entry import check_entry
from app.strategy.exit import calculate_stop_loss, calculate_take_profit
from app.utils.math_utils import pips_to_price
from app.utils.time_utils import is_in_session

logger = get_logger("strategy.engine")


class StrategyEngine:
    """Orchestrates the trading strategy analysis pipeline.

    All analysis uses CLOSED candles only. The engine does not handle
    execution timing — that's the backtest engine's job.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.strategy_config = self.settings.strategy
        self.symbols_config = self.settings.symbols

    def analyze(
        self,
        h1_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        symbol: str,
        current_time: datetime | None = None,
    ) -> TradeIdea | None:
        """Run the full strategy pipeline on closed candle data.

        Args:
            h1_df: H1 OHLC DataFrame (CLOSED candles only — df.iloc[:i]).
            h4_df: H4 OHLC DataFrame (CLOSED candles only — synced to current time).
            symbol: Trading symbol (e.g., 'EURUSD').
            current_time: Timestamp of the analysis (for session filtering).

        Returns:
            TradeIdea if all gates pass, None otherwise.
        """
        reasoning = {}

        # ──────────────────────────────────────────────
        # Gate 1: Session filter
        # ──────────────────────────────────────────────
        if current_time is not None:
            in_session = is_in_session(current_time, self.strategy_config.trading_sessions)
            reasoning["session_filter"] = {
                "time": str(current_time),
                "sessions": self.strategy_config.trading_sessions,
                "in_session": in_session,
            }
            if not in_session:
                logger.debug("Rejected: outside trading session", symbol=symbol)
                return None

        # ──────────────────────────────────────────────
        # Gate 2: ATR threshold (skip low-vol chop)
        # ──────────────────────────────────────────────
        atr = calculate_atr(h1_df, period=self.strategy_config.atr_period)
        reasoning["atr"] = {
            "value": atr,
            "threshold": self.strategy_config.min_atr_threshold,
        }

        if atr is None:
            logger.debug("Rejected: ATR calculation failed", symbol=symbol)
            return None

        if atr < self.strategy_config.min_atr_threshold:
            reasoning["atr"]["passed"] = False
            logger.debug(
                f"Rejected: ATR {atr:.5f} below threshold "
                f"{self.strategy_config.min_atr_threshold}",
                symbol=symbol,
            )
            return None
        reasoning["atr"]["passed"] = True

        # ──────────────────────────────────────────────
        # Gate 3: Trend detection (H4)
        # ──────────────────────────────────────────────
        trend = detect_trend(
            h4_df,
            ema_fast_period=self.strategy_config.ema_fast,
            ema_slow_period=self.strategy_config.ema_slow,
        )
        reasoning["trend"] = {
            "direction": trend.value if trend else "NONE",
            "method": self.strategy_config.trend_method,
            "ema_fast": self.strategy_config.ema_fast,
            "ema_slow": self.strategy_config.ema_slow,
        }

        if trend is None:
            logger.debug("Rejected: no clear trend", symbol=symbol)
            return None

        # ──────────────────────────────────────────────
        # Gate 4: Pullback detection (H1)
        # ──────────────────────────────────────────────
        pullback = detect_pullback(
            h1_df,
            trend_direction=trend,
            pullback_ema_period=self.strategy_config.pullback_ema,
        )
        reasoning["pullback"] = {"detected": pullback}

        if not pullback:
            logger.debug("Rejected: no pullback detected", symbol=symbol)
            return None

        # ──────────────────────────────────────────────
        # Gate 5: Entry confirmation (H1)
        # ──────────────────────────────────────────────
        signal_close = check_entry(
            h1_df,
            trend_direction=trend,
            min_body_ratio=self.strategy_config.min_body_ratio,
        )
        reasoning["entry"] = {
            "signal_close": signal_close,
            "min_body_ratio": self.strategy_config.min_body_ratio,
        }

        if signal_close is None:
            logger.debug("Rejected: entry candle not confirmed", symbol=symbol)
            return None

        # ──────────────────────────────────────────────
        # Gate 6: Exit calculation (SL + TP)
        # ──────────────────────────────────────────────
        # Calculate minimum SL distance from config (pips → price)
        min_sl_distance = pips_to_price(
            self.strategy_config.min_sl_pips, symbol, self.symbols_config
        )

        sl = calculate_stop_loss(
            entry_price=signal_close,
            atr=atr,
            direction=trend,
            atr_multiplier=self.strategy_config.atr_multiplier,
            min_sl_distance=min_sl_distance,
        )

        tp = calculate_take_profit(
            entry_price=signal_close,
            stop_loss=sl,
            direction=trend,
            rr_ratio=self.strategy_config.rr_ratio,
        )

        sl_distance = abs(signal_close - sl)
        tp_distance = abs(tp - signal_close)
        rr = tp_distance / sl_distance if sl_distance > 0 else 0

        reasoning["exit"] = {
            "stop_loss": round(sl, 5),
            "take_profit": round(tp, 5),
            "sl_distance": round(sl_distance, 5),
            "tp_distance": round(tp_distance, 5),
            "risk_reward": round(rr, 2),
        }

        # ──────────────────────────────────────────────
        # Build TradeIdea
        # ──────────────────────────────────────────────
        trade_idea = TradeIdea(
            symbol=symbol,
            direction=trend,
            entry_price=signal_close,  # Backtest engine replaces with next open
            stop_loss=sl,
            take_profit=tp,
            atr=atr,
            risk_reward=rr,
            timestamp=current_time or datetime.utcnow(),
            reasoning=reasoning,
        )

        logger.info(
            "🟢 Trade signal generated",
            symbol=symbol,
            direction=trend.value,
            entry=round(signal_close, 5),
            sl=round(sl, 5),
            tp=round(tp, 5),
            rr=round(rr, 2),
            atr=round(atr, 5),
        )

        return trade_idea
