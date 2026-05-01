"""
Configuration system — loads YAML config with pydantic validation.
Every strategy parameter is config-driven. Zero hardcoding.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
    print(settings.strategy.ema_fast)  # 50
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator


# ═══════════════════════════════════════════════════════════════
#  Config sub-models
# ═══════════════════════════════════════════════════════════════


class SymbolConfig(BaseModel):
    """Per-symbol trading parameters."""
    pip_size: float
    contract_size: int


class RiskConfig(BaseModel):
    """Risk management parameters."""
    per_trade: float = 0.02
    max_trades_per_session: int = 3
    max_daily_drawdown: float = 0.05


class StrategyConfig(BaseModel):
    """Strategy parameters — v3 Volatility Breakout."""
    trend_method: str = "ema"
    ema_fast: int = 50
    ema_slow: int = 200

    # Volatility squeeze detection
    squeeze_atr_fast: int = 14
    squeeze_atr_slow: int = 50
    squeeze_ratio: float = 0.85
    min_squeeze_bars: int = 3

    # Breakout detection
    breakout_channel: int = 48
    min_breakout_atr_mult: float = 0.5

    # Exits
    initial_sl_atr: float = 1.5
    rr_ratio: float = 2.5

    # Filters
    min_atr_threshold: float = 0.0005
    min_sl_pips: float = 5.0
    min_bars_between_trades: int = 15
    allow_multiple_positions: bool = False
    trading_sessions: list[str] = ["LONDON", "NEW_YORK"]


class TimeframeConfig(BaseModel):
    """Explicit timeframe assignment — never mix."""
    execution: str = "H1"   # Entry, pullback, ATR
    trend: str = "H4"       # Trend detection


class BacktestConfig(BaseModel):
    """Backtest simulation parameters."""
    spread_pips: float = 1.5
    slippage_pips: float = 0.5
    initial_balance: float = 10000.0
    execution_mode: str = "conservative"
    min_trades: int = 100

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        valid = {"conservative", "optimistic", "random"}
        if v not in valid:
            raise ValueError(f"execution_mode must be one of {valid}, got '{v}'")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"


# ═══════════════════════════════════════════════════════════════
#  Main Settings model
# ═══════════════════════════════════════════════════════════════


class Settings(BaseModel):
    """Root configuration — aggregates all sub-configs."""
    account_currency: str = "USD"
    symbols: dict[str, SymbolConfig] = {}
    risk: RiskConfig = RiskConfig()
    strategy: StrategyConfig = StrategyConfig()
    timeframes: TimeframeConfig = TimeframeConfig()
    backtest: BacktestConfig = BacktestConfig()
    logging: LoggingConfig = LoggingConfig()


def _find_config_path() -> Path:
    """Locate the config file. Checks env var first, then default location."""
    env_path = os.environ.get("FOREXBOT_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Default: configs/default.yaml relative to project root
    project_root = Path(__file__).parent.parent.parent
    default_path = project_root / "configs" / "default.yaml"
    if default_path.exists():
        return default_path

    raise FileNotFoundError(
        "Config file not found. Set FOREXBOT_CONFIG env var or create configs/default.yaml"
    )


def load_settings(config_path: Path | str | None = None) -> Settings:
    """Load and validate settings from YAML file.

    Args:
        config_path: Optional explicit path. If None, auto-discovers.

    Returns:
        Validated Settings object.
    """
    if config_path is None:
        path = _find_config_path()
    else:
        path = Path(config_path)

    with open(path, "r") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    return Settings(**raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for global settings. Cached after first call."""
    return load_settings()
