"""
Shared test fixtures — sample DataFrames, config objects.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import load_settings, Settings, SymbolConfig


@pytest.fixture
def settings() -> Settings:
    """Load test settings from default config."""
    config_path = Path(__file__).parent.parent / "configs" / "default.yaml"
    return load_settings(config_path)


@pytest.fixture
def symbols_config() -> dict[str, SymbolConfig]:
    """Symbol configs for testing."""
    return {
        "EURUSD": SymbolConfig(pip_size=0.0001, contract_size=100000),
        "GBPUSD": SymbolConfig(pip_size=0.0001, contract_size=100000),
        "XAUUSD": SymbolConfig(pip_size=0.1, contract_size=100),
        "USDJPY": SymbolConfig(pip_size=0.01, contract_size=100000),
    }


def _make_ohlc(
    n: int,
    start_price: float = 1.1000,
    trend: str = "up",
    volatility: float = 0.001,
    start_time: datetime | None = None,
    interval_hours: int = 1,
) -> pd.DataFrame:
    """Generate synthetic OHLC data with a controlled trend.

    Args:
        n: Number of bars.
        start_price: Starting close price.
        trend: 'up', 'down', or 'flat'.
        volatility: Price movement per bar.
        start_time: First bar timestamp.
        interval_hours: Hours between bars.
    """
    if start_time is None:
        start_time = datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)

    np.random.seed(42)
    prices = [start_price]

    for i in range(1, n):
        if trend == "up":
            drift = volatility * 0.3
        elif trend == "down":
            drift = -volatility * 0.3
        else:
            drift = 0

        noise = np.random.normal(0, volatility)
        prices.append(prices[-1] + drift + noise)

    data = []
    for i, close in enumerate(prices):
        spread = volatility * np.random.uniform(0.5, 2.0)
        high = close + abs(spread)
        low = close - abs(spread)
        open_price = prices[i - 1] if i > 0 else close
        t = start_time + timedelta(hours=i * interval_hours)

        data.append({
            "time": t,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.random.randint(100, 10000),
        })

    return pd.DataFrame(data)


@pytest.fixture
def uptrend_h1_df() -> pd.DataFrame:
    """300 bars of H1 uptrend data during London session."""
    return _make_ohlc(300, start_price=1.1000, trend="up", interval_hours=1)


@pytest.fixture
def downtrend_h1_df() -> pd.DataFrame:
    """300 bars of H1 downtrend data."""
    return _make_ohlc(300, start_price=1.2000, trend="down", interval_hours=1)


@pytest.fixture
def flat_h1_df() -> pd.DataFrame:
    """300 bars of ranging H1 data."""
    return _make_ohlc(300, start_price=1.1500, trend="flat", volatility=0.0003, interval_hours=1)


@pytest.fixture
def uptrend_h4_df() -> pd.DataFrame:
    """300 bars of H4 uptrend data."""
    return _make_ohlc(300, start_price=1.1000, trend="up", interval_hours=4)


@pytest.fixture
def downtrend_h4_df() -> pd.DataFrame:
    """300 bars of H4 downtrend data."""
    return _make_ohlc(300, start_price=1.2000, trend="down", interval_hours=4)
