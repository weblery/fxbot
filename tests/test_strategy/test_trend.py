"""Tests for trend detection module."""

from app.core.constants import TradeDirection
from app.strategy.trend import detect_trend


class TestDetectTrend:
    def test_uptrend_detected(self, uptrend_h4_df):
        result = detect_trend(uptrend_h4_df)
        assert result == TradeDirection.LONG

    def test_downtrend_detected(self, downtrend_h4_df):
        result = detect_trend(downtrend_h4_df)
        assert result == TradeDirection.SHORT

    def test_insufficient_data(self):
        import pandas as pd
        tiny_df = pd.DataFrame({
            "time": range(10),
            "open": [1.0] * 10,
            "high": [1.1] * 10,
            "low": [0.9] * 10,
            "close": [1.0] * 10,
            "volume": [100] * 10,
        })
        result = detect_trend(tiny_df)
        assert result is None
