"""Tests for backtest simulator — execution modes and cost application."""

from datetime import datetime, timezone

from app.core.config import load_settings
from app.core.constants import TradeDirection, TradeState
from app.models.trade import TradeIdea, TradeResult
from app.backtesting.simulator import TradeSimulator


class TestTradeSimulator:
    def setup_method(self):
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "configs" / "default.yaml"
        self.settings = load_settings(config_path)
        self.sim = TradeSimulator(self.settings)

    def test_spread_applied_long(self):
        price = 1.1000
        adjusted = self.sim.apply_entry_costs(price, TradeDirection.LONG, "EURUSD")
        # LONG: price + spread + slippage → should be higher
        assert adjusted > price

    def test_spread_applied_short(self):
        price = 1.1000
        adjusted = self.sim.apply_entry_costs(price, TradeDirection.SHORT, "EURUSD")
        # SHORT: price - spread - slippage → should be lower
        assert adjusted < price

    def test_sl_hit_long(self):
        idea = TradeIdea(
            symbol="EURUSD", direction=TradeDirection.LONG,
            entry_price=1.1000, stop_loss=1.0950, take_profit=1.1100,
            atr=0.0025, risk_reward=2.0,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        trade = TradeResult(trade_idea=idea, state=TradeState.OPEN)

        result = self.sim.check_sl_tp(
            trade, bar_high=1.1020, bar_low=1.0940,
            bar_close=1.0960,
            bar_time=datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
            symbol="EURUSD",
        )
        assert result is not None
        assert result.state == TradeState.STOPPED

    def test_tp_hit_long(self):
        idea = TradeIdea(
            symbol="EURUSD", direction=TradeDirection.LONG,
            entry_price=1.1000, stop_loss=1.0950, take_profit=1.1100,
            atr=0.0025, risk_reward=2.0,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        trade = TradeResult(trade_idea=idea, state=TradeState.OPEN)

        result = self.sim.check_sl_tp(
            trade, bar_high=1.1120, bar_low=1.0980,
            bar_close=1.1100,
            bar_time=datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
            symbol="EURUSD",
        )
        assert result is not None
        assert result.state == TradeState.TARGET_HIT

    def test_no_hit(self):
        idea = TradeIdea(
            symbol="EURUSD", direction=TradeDirection.LONG,
            entry_price=1.1000, stop_loss=1.0950, take_profit=1.1100,
            atr=0.0025, risk_reward=2.0,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        trade = TradeResult(trade_idea=idea, state=TradeState.OPEN)

        result = self.sim.check_sl_tp(
            trade, bar_high=1.1050, bar_low=1.0970,
            bar_close=1.1020,
            bar_time=datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
            symbol="EURUSD",
        )
        assert result is None
