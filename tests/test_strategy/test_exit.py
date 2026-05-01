"""Tests for exit (SL/TP) calculation."""

from app.core.constants import TradeDirection
from app.strategy.exit import calculate_stop_loss, calculate_take_profit


class TestExitCalculation:
    def test_long_sl_below_entry(self):
        sl = calculate_stop_loss(1.1000, atr=0.0010, direction=TradeDirection.LONG)
        assert sl < 1.1000

    def test_short_sl_above_entry(self):
        sl = calculate_stop_loss(1.1000, atr=0.0010, direction=TradeDirection.SHORT)
        assert sl > 1.1000

    def test_min_sl_floor(self):
        # ATR-based SL = 0.0001 * 2 = 0.0002 (very small)
        # min_sl = 0.0005 (should override)
        sl = calculate_stop_loss(
            1.1000, atr=0.0001, direction=TradeDirection.LONG,
            atr_multiplier=2.0, min_sl_distance=0.0005,
        )
        assert abs(1.1000 - sl) >= 0.0005 - 1e-10  # tolerance for float math

    def test_tp_respects_rr(self):
        sl = calculate_stop_loss(1.1000, atr=0.0010, direction=TradeDirection.LONG)
        tp = calculate_take_profit(1.1000, sl, TradeDirection.LONG, rr_ratio=2.0)
        sl_dist = abs(1.1000 - sl)
        tp_dist = abs(tp - 1.1000)
        assert abs(tp_dist - 2 * sl_dist) < 0.00001
