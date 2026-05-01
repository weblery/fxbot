"""
Data fetcher — retrieves OHLC candle data from MT5 or local storage.
Supports multiple timeframes for multi-timeframe analysis.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.constants import Timeframe, MT5_TIMEFRAME_MAP
from app.core.logger import get_logger
from app.data.mt5_client import MT5Client
from app.utils.decorators import retry

logger = get_logger("data.fetcher")


class DataFetcher:
    """Fetches market data from MT5 terminal.

    If MT5 is not available (non-Windows), returns empty DataFrames.
    Use DataStorage to load cached CSV data instead.
    """

    def __init__(self, mt5_client: MT5Client | None = None):
        self.client = mt5_client

    @retry(max_attempts=3, delay=1.0)
    def fetch_ohlc(
        self,
        symbol: str,
        timeframe: Timeframe,
        num_bars: int = 1000,
    ) -> pd.DataFrame:
        """Fetch OHLC candle data from MT5.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD').
            timeframe: Chart timeframe.
            num_bars: Number of historical bars to fetch.

        Returns:
            DataFrame with columns: time, open, high, low, close, volume
        """
        mt5 = self.client.get_mt5() if self.client else None

        if mt5 is None:
            logger.warning(f"MT5 not available. Cannot fetch {symbol} {timeframe.value}")
            return pd.DataFrame()

        mt5_tf = MT5_TIMEFRAME_MAP.get(timeframe)
        if mt5_tf is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, num_bars)

        if rates is None or len(rates) == 0:
            logger.error(f"No data returned for {symbol} {timeframe.value}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        logger.info(
            f"Fetched {len(df)} bars",
            symbol=symbol,
            timeframe=timeframe.value,
            bars=len(df),
        )
        return df

    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: list[Timeframe],
        num_bars: int = 1000,
    ) -> dict[str, pd.DataFrame]:
        """Fetch data for multiple timeframes.

        Args:
            symbol: Trading symbol.
            timeframes: List of timeframes to fetch.
            num_bars: Bars per timeframe.

        Returns:
            Dict mapping timeframe name to DataFrame.
        """
        result = {}
        for tf in timeframes:
            result[tf.value] = self.fetch_ohlc(symbol, tf, num_bars)
        return result
