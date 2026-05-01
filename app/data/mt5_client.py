"""
MetaTrader 5 client — handles connection lifecycle.

NOTE: MT5 Python API only works on Windows.
On macOS/Linux, this module will log a warning and provide stub behavior
for development. Live trading requires a Windows VPS.
"""

from __future__ import annotations

import platform
import sys

from app.core.logger import get_logger
from app.utils.decorators import retry

logger = get_logger("data.mt5_client")

# Check platform — MT5 only runs on Windows
_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        mt5 = None  # type: ignore[assignment]
        logger.warning("MetaTrader5 package not installed. Run: pip install MetaTrader5")
else:
    mt5 = None  # type: ignore[assignment]
    logger.info("Non-Windows platform detected. MT5 client will use stub mode for development.")


class MT5Client:
    """MetaTrader 5 connection manager with context manager support.

    Usage:
        with MT5Client(login=123, password='xxx', server='Broker') as client:
            # client is connected
            data = client.copy_rates(...)
    """

    def __init__(
        self,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
    ):
        self.login = login
        self.password = password
        self.server = server
        self._connected = False

    def __enter__(self) -> "MT5Client":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    @retry(max_attempts=3, delay=2.0)
    def connect(self) -> bool:
        """Initialize MT5 terminal and log in.

        Returns:
            True if connection successful.

        Raises:
            RuntimeError: If MT5 is not available or connection fails.
        """
        if mt5 is None:
            logger.warning("MT5 not available on this platform. Running in stub mode.")
            self._connected = False
            return False

        if not mt5.initialize():
            error = mt5.last_error()
            raise RuntimeError(f"MT5 initialization failed: {error}")

        if self.login and self.password and self.server:
            authorized = mt5.login(
                login=self.login,
                password=self.password,
                server=self.server,
            )
            if not authorized:
                error = mt5.last_error()
                mt5.shutdown()
                raise RuntimeError(f"MT5 login failed: {error}")

        self._connected = True
        logger.info("MT5 connected successfully", login=self.login, server=self.server)
        return True

    def disconnect(self) -> None:
        """Shutdown MT5 terminal connection."""
        if mt5 is not None and self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_mt5(self):
        """Get the raw MT5 module for direct API calls.

        Returns:
            The MetaTrader5 module, or None if not available.
        """
        return mt5
