"""
Drawdown tracker — monitors account equity for kill switch decisions.

Tracks peak equity and current equity to calculate drawdown percentage.
Triggers trading halt when max drawdown threshold is breached.
"""

from __future__ import annotations

from app.core.logger import get_logger

logger = get_logger("risk.drawdown")


class DrawdownTracker:
    """Tracks account drawdown and provides a kill switch.

    Usage:
        tracker = DrawdownTracker(initial_balance=10000, max_drawdown_pct=0.05)
        tracker.update_equity(9800)

        if tracker.should_stop_trading():
            # HALT — drawdown exceeded
    """

    def __init__(self, initial_balance: float, max_drawdown_pct: float = 0.05):
        """
        Args:
            initial_balance: Starting account balance.
            max_drawdown_pct: Maximum allowed drawdown as decimal (0.05 = 5%).
        """
        self.initial_balance = initial_balance
        self.max_drawdown_pct = max_drawdown_pct
        self.peak_equity = initial_balance
        self.current_equity = initial_balance

    def update_equity(self, equity: float) -> None:
        """Update current equity and track new peaks.

        Args:
            equity: Current account equity.
        """
        self.current_equity = equity
        if equity > self.peak_equity:
            self.peak_equity = equity

    def current_drawdown_pct(self) -> float:
        """Calculate current drawdown as a percentage of peak equity.

        Returns:
            Drawdown percentage (e.g., 0.03 = 3%).
        """
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity

    def current_drawdown_amount(self) -> float:
        """Calculate current drawdown in absolute currency.

        Returns:
            Drawdown amount.
        """
        return self.peak_equity - self.current_equity

    def should_stop_trading(self) -> bool:
        """Check if drawdown exceeds the maximum threshold.

        Returns:
            True if trading should be halted.
        """
        dd = self.current_drawdown_pct()
        if dd >= self.max_drawdown_pct:
            logger.warning(
                f"Drawdown kill switch triggered: {dd:.1%} >= {self.max_drawdown_pct:.1%}",
                drawdown_pct=round(dd, 4),
                peak=self.peak_equity,
                current=self.current_equity,
            )
            return True
        return False

    def reset(self, new_balance: Optional[float] = None) -> None:
        """Reset tracker (e.g., at start of new trading day).

        Args:
            new_balance: Optional new starting balance. If None, uses current equity.
        """
        balance = new_balance or self.current_equity
        self.peak_equity = balance
        self.current_equity = balance
