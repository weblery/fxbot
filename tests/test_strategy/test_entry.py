"""Tests for entry confirmation."""

import pandas as pd
from app.core.constants import TradeDirection
from app.strategy.entry import check_entry


class TestCheckEntry:
    def test_bullish_candle_long_entry(self):
        df = pd.DataFrame({
            "open": [1.0, 1.05],
            "high": [1.02, 1.10],
            "low": [0.98, 1.04],
            "close": [1.01, 1.09],
            "volume": [100, 200],
        })
        result = check_entry(df, TradeDirection.LONG, min_body_ratio=0.6)
        assert result is not None
        assert result == 1.09

    def test_bearish_candle_rejects_long(self):
        df = pd.DataFrame({
            "open": [1.0, 1.10],
            "high": [1.02, 1.11],
            "low": [0.98, 1.03],
            "close": [1.01, 1.05],
            "volume": [100, 200],
        })
        result = check_entry(df, TradeDirection.LONG, min_body_ratio=0.6)
        assert result is None

    def test_weak_body_rejected(self):
        # Doji-like candle — body < 60% of range
        df = pd.DataFrame({
            "open": [1.0, 1.050],
            "high": [1.02, 1.100],
            "low": [0.98, 1.000],
            "close": [1.01, 1.055],  # tiny body, big wicks
            "volume": [100, 200],
        })
        result = check_entry(df, TradeDirection.LONG, min_body_ratio=0.6)
        assert result is None

    def test_short_entry(self):
        df = pd.DataFrame({
            "open": [1.10, 1.05],
            "high": [1.11, 1.06],
            "low": [1.09, 0.98],
            "close": [1.09, 0.99],
            "volume": [100, 200],
        })
        result = check_entry(df, TradeDirection.SHORT, min_body_ratio=0.6)
        assert result is not None
