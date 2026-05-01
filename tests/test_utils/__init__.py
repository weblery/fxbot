"""Tests for math utilities."""

from app.core.config import SymbolConfig
from app.utils.math_utils import (
    get_pip_value, get_pip_size, pips_to_price, price_to_pips, round_lot_size,
)


class TestMathUtils:
    def setup_method(self):
        self.symbols = {
            "EURUSD": SymbolConfig(pip_size=0.0001, contract_size=100000),
            "USDJPY": SymbolConfig(pip_size=0.01, contract_size=100000),
            "XAUUSD": SymbolConfig(pip_size=0.1, contract_size=100),
        }

    def test_eurusd_pip_value(self):
        # 1 lot EURUSD: 0.0001 * 100,000 * 1.0 = $10
        pv = get_pip_value("EURUSD", 1.0, self.symbols)
        assert pv == 10.0

    def test_xauusd_pip_value(self):
        # 1 lot XAUUSD: 0.1 * 100 * 1.0 = $10
        pv = get_pip_value("XAUUSD", 1.0, self.symbols)
        assert pv == 10.0

    def test_usdjpy_pip_size(self):
        ps = get_pip_size("USDJPY", self.symbols)
        assert ps == 0.01

    def test_pips_to_price_eurusd(self):
        # 10 pips on EURUSD = 0.0010
        dist = pips_to_price(10, "EURUSD", self.symbols)
        assert abs(dist - 0.0010) < 1e-10

    def test_price_to_pips_xauusd(self):
        # $2 movement on XAUUSD = 20 pips (pip_size=0.1)
        pips = price_to_pips(2.0, "XAUUSD", self.symbols)
        assert abs(pips - 20.0) < 1e-10

    def test_round_lot_size(self):
        assert round_lot_size(0.123) == 0.12
        assert round_lot_size(0.001) == 0.01
        assert round_lot_size(1.999) == 1.99
