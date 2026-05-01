"""
Centralized logging — structured JSON to file, human-readable to console.
Every trading decision is traceable.

Usage:
    from app.core.logger import setup_logging, get_logger
    setup_logging()
    logger = get_logger("strategy.engine")
    logger.info("Trade signal", symbol="EURUSD", direction="LONG", atr=0.0012)
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(level: str = "INFO", log_format: str = "json") -> None:
    """Configure loguru with console + file sinks.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        log_format: 'json' for structured file output, 'text' for plain.
    """
    # Remove default handler
    logger.remove()

    # Console sink — always human-readable
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[module]}</cyan> | "
            "{message}"
        ),
        colorize=True,
    )

    # File sink — structured JSON for analysis
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    if log_format == "json":
        logger.add(
            log_dir / "forexbot_{time:YYYY-MM-DD}.log",
            level=level,
            format="{message}",
            serialize=True,            # loguru's built-in JSON serialization
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )
    else:
        logger.add(
            log_dir / "forexbot_{time:YYYY-MM-DD}.log",
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[module]} | {message}",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )


def get_logger(module_name: str = "root") -> logger.__class__:
    """Get a logger instance bound to a specific module name.

    Args:
        module_name: Dot-separated module path (e.g., 'strategy.engine').

    Returns:
        Bound loguru logger instance.
    """
    return logger.bind(module=module_name)
