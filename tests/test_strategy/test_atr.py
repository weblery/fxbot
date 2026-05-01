"""Tests for ATR calculation."""

from app.strategy.atr import calculate_atr


class TestCalculateATR:
    def test_atr_returns_float(self, uptrend_h1_df):
        result = calculate_atr(uptrend_h1_df, period=14)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_atr_insufficient_data(self):
        import pandas as pd
        tiny = pd.DataFrame({
            "high": [1.1] * 5,
            "low": [0.9] * 5,
            "close": [1.0] * 5,
        })
        result = calculate_atr(tiny, period=14)
        assert result is None
