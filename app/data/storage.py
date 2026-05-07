"""
Data storage — CSV-based cache for historical market data.
Saves fetched data locally to avoid repeated MT5 calls.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from app.core.logger import get_logger
from app.data.transformer import transform_raw_data

logger = get_logger("data.storage")


class DataStorage:
    """Manages local CSV storage for historical OHLC data.

    Storage path: data/{symbol}_{timeframe}.csv
    """

    def __init__(self, data_dir: str | Optional[Path] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, symbol: str, timeframe: str) -> Path:
        """Build the CSV filepath for a symbol/timeframe pair."""
        return self.data_dir / f"{symbol}_{timeframe}.csv"

    def save(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Path:
        """Save a DataFrame to CSV.

        Args:
            df: OHLC DataFrame to save.
            symbol: Trading symbol.
            timeframe: Chart timeframe string (e.g., 'H1').

        Returns:
            Path to the saved file.
        """
        filepath = self._get_filepath(symbol, timeframe)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} bars to {filepath}", symbol=symbol, timeframe=timeframe)
        return filepath

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load a DataFrame from CSV and transform it.

        Args:
            symbol: Trading symbol.
            timeframe: Chart timeframe string.

        Returns:
            Transformed DataFrame, or empty DataFrame if file doesn't exist.
        """
        filepath = self._get_filepath(symbol, timeframe)

        if not filepath.exists():
            logger.warning(f"No cached data found at {filepath}")
            return pd.DataFrame()

        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} bars from {filepath}", symbol=symbol, timeframe=timeframe)
        return transform_raw_data(df)

    def exists(self, symbol: str, timeframe: str) -> bool:
        """Check if cached data exists for a symbol/timeframe pair."""
        return self._get_filepath(symbol, timeframe).exists()

    def is_fresh(
        self, symbol: str, timeframe: str, max_age_hours: int = 24
    ) -> bool:
        """Check if cached data is recent enough to use.

        Args:
            symbol: Trading symbol.
            timeframe: Chart timeframe string.
            max_age_hours: Maximum age in hours before data is considered stale.

        Returns:
            True if file exists and was modified within max_age_hours.
        """
        filepath = self._get_filepath(symbol, timeframe)
        if not filepath.exists():
            return False

        modified = datetime.fromtimestamp(filepath.stat().st_mtime)
        age = datetime.now() - modified
        return age < timedelta(hours=max_age_hours)
