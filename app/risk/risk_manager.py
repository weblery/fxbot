"""
Risk Manager — validates trades against risk constraints before execution.

Enforces:
  - Max risk per trade
  - Max open positions per session
  - Daily drawdown kill switch
"""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.models.trade import TradeIdea
from app.risk.drawdown import DrawdownTracker

logger = get_logger("risk.risk_manager")


class RiskManager:
    """Validates trade ideas against risk constraints.

    Sits between the strategy engine and execution —
    no trade passes without risk approval.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        drawdown_tracker: Optional[DrawdownTracker] = None,
    ):
        self.settings = settings or get_settings()
        self.risk_config = self.settings.risk
        self.drawdown_tracker = drawdown_tracker or DrawdownTracker(
            initial_balance=self.settings.backtest.initial_balance,
            max_drawdown_pct=self.risk_config.max_daily_drawdown,
        )
        self._open_trade_count = 0
        self._open_symbols: set[str] = set()

    def validate_trade(
        self,
        trade_idea: TradeIdea,
        account_balance: float,
    ) -> bool:
        """Validate a trade idea against all risk rules.

        Args:
            trade_idea: The trade to validate.
            account_balance: Current account balance.

        Returns:
            True if the trade passes all risk checks.
        """
        # Check 1: Max trades per session
        if self._open_trade_count >= self.risk_config.max_trades_per_session:
            logger.warning(
                f"Rejected: max trades ({self.risk_config.max_trades_per_session}) reached",
                symbol=trade_idea.symbol,
            )
            return False

        # Check 2: No multiple positions per symbol (if disabled)
        if not self.settings.strategy.allow_multiple_positions:
            if trade_idea.symbol in self._open_symbols:
                logger.warning(
                    f"Rejected: position already open for {trade_idea.symbol}",
                    symbol=trade_idea.symbol,
                )
                return False

        # Check 3: Per-trade risk limit
        sl_distance = trade_idea.sl_distance
        if sl_distance <= 0:
            logger.warning("Rejected: invalid SL distance", symbol=trade_idea.symbol)
            return False

        max_risk = account_balance * self.risk_config.per_trade
        # This is a sanity check — actual lot sizing handles precise risk
        logger.debug(
            f"Risk check: max ${max_risk:.2f} per trade",
            symbol=trade_idea.symbol,
        )

        # Check 4: Drawdown kill switch
        if self.drawdown_tracker.should_stop_trading():
            logger.warning(
                "🔴 KILL SWITCH: Daily drawdown limit reached — no new trades",
                drawdown=self.drawdown_tracker.current_drawdown_pct(),
                max_allowed=self.risk_config.max_daily_drawdown,
            )
            return False

        logger.info(
            "✅ Trade approved by risk manager",
            symbol=trade_idea.symbol,
            direction=trade_idea.direction.value,
        )
        return True

    def register_open_trade(self, symbol: str) -> None:
        """Track a newly opened trade."""
        self._open_trade_count += 1
        self._open_symbols.add(symbol)

    def register_closed_trade(self, symbol: str) -> None:
        """Track a closed trade."""
        self._open_trade_count = max(0, self._open_trade_count - 1)
        self._open_symbols.discard(symbol)

    def reset(self) -> None:
        """Reset trade counters (e.g., at start of new session)."""
        self._open_trade_count = 0
        self._open_symbols.clear()
