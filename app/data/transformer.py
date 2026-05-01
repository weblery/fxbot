"""
Data transformer — cleans and standardizes raw OHLC data.
All DataFrames flowing through the system use a consistent format.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.core.logger import get_logger

logger = get_logger("data.transformer")

# Standard column names used throughout the system
STANDARD_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


def transform_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize raw OHLC data into the system format.

    Performs:
    - Column name standardization (lowercase)
    - Timestamp conversion to datetime (UTC)
    - Sorting by time (ascending)
    - NaN/gap detection and forward-fill
    - Index reset

    Args:
        df: Raw DataFrame (e.g., from MT5 or CSV).

    Returns:
        Cleaned DataFrame with standard columns and datetime index info.
    """
    if df.empty:
        logger.warning("Empty DataFrame received — returning empty")
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    # Make a copy to avoid mutating the original
    result = df.copy()

    # Standardize column names to lowercase
    result.columns = [col.lower().strip() for col in result.columns]

    # Handle MT5 timestamp format (Unix epoch seconds)
    if "time" in result.columns:
        if result["time"].dtype in [np.int64, np.int32, np.float64]:
            result["time"] = pd.to_datetime(result["time"], unit="s", utc=True)
        elif not pd.api.types.is_datetime64_any_dtype(result["time"]):
            result["time"] = pd.to_datetime(result["time"], utc=True)

    # Ensure required columns exist
    for col in STANDARD_COLUMNS:
        if col not in result.columns:
            logger.error(f"Missing required column: {col}")
            raise ValueError(f"Missing required column: '{col}'")

    # Keep only standard columns (drop tick_volume, spread, etc.)
    result = result[STANDARD_COLUMNS].copy()

    # Sort by time ascending
    result = result.sort_values("time").reset_index(drop=True)

    # Handle NaN values
    nan_count = result[["open", "high", "low", "close"]].isna().sum().sum()
    if nan_count > 0:
        logger.warning(f"Found {nan_count} NaN values — forward-filling")
        result[["open", "high", "low", "close"]] = (
            result[["open", "high", "low", "close"]].ffill()
        )

    # Drop any remaining rows with NaN (e.g., at the very start)
    result = result.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    logger.debug(
        f"Transformed {len(result)} bars",
        start=str(result["time"].iloc[0]) if len(result) > 0 else "N/A",
        end=str(result["time"].iloc[-1]) if len(result) > 0 else "N/A",
    )

    return result
