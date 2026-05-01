"""Tests for position sizing."""

from app.core.config import SymbolConfig
from app.risk.position_sizing import calculate_position_size


class TestPositionSizing:
    def setup_method(self):
        self.symbols = {
            "EURUSD": SymbolConfig(pip_size=0.0001, contract_size=100000),
            "XAUUSD": SymbolConfig(pip_size=0.1, contract_size=100),
        }

    def test_standard_lot_calculation(self):
        lot = calculate_position_size(
            account_balance=10000,
            risk_percent=0.02,
            sl_distance=0.0020,
            symbol="EURUSD",
            symbols_config=self.symbols,
        )
        assert lot > 0
        assert lot <= 10.0

    def test_gold_position_sizing(self):
        lot = calculate_position_size(
            account_balance=10000,
            risk_percent=0.02,
            sl_distance=2.0,
            symbol="XAUUSD",
            symbols_config=self.symbols,
        )
        assert lot > 0

    def test_minimum_lot_enforced(self):
        lot = calculate_position_size(
            account_balance=100,
            risk_percent=0.01,
            sl_distance=0.0100,
            symbol="EURUSD",
            symbols_config=self.symbols,
            min_lot=0.01,
        )
        assert lot >= 0.01
