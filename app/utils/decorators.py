"""
Reusable decorators for error handling and performance tracking.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from loguru import logger

F = TypeVar("F", bound=Callable[..., Any])


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Retry a function on failure with configurable attempts and delay.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Seconds to wait between retries.
        exceptions: Tuple of exception types to catch and retry on.

    Usage:
        @retry(max_attempts=3, delay=2.0)
        def fetch_data():
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    log = logger.bind(module="decorators")
                    log.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}"
                    )
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def log_execution_time(func: F) -> F:
    """Log the execution time of a function.

    Usage:
        @log_execution_time
        def slow_operation():
            ...
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        log = logger.bind(module="performance")
        log.debug(f"{func.__name__} completed in {elapsed:.4f}s")
        return result

    return wrapper  # type: ignore[return-value]
