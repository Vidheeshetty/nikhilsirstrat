from __future__ import annotations

"""Single instrument back-test runner for the Trend-Riding strategy.

For now it plugs together the in-memory stub ``BacktestEngine`` with the
placeholder strategy implementation.  Later we can replace the stub with the
real Nautilus engine while keeping the public API stable.
"""

from typing import Dict, Any, List

from strategies.trend_riding.strategy import TrendRidingStrategy
from strategies.trend_riding.config import TrendRidingConfig
from utils.runners.engine_manager import EngineManager
from utils.data.data_manager import DataManager


class TrendRidingBacktestRunner:  # pylint: disable=too-few-public-methods
    """Execute a back-test for one instrument and return a summary dict."""

    def __init__(self, prices_provider=None):
        """Optionally inject a callable that returns a list of float prices."""
        self._prices_provider = prices_provider or self._dummy_prices

    # ------------------------------------------------------------------
    @staticmethod
    def _dummy_prices(instrument_id: str) -> List[float]:  # noqa: D401
        """Generate a monotonically rising price series – deterministic stub."""
        base = sum(ord(ch) for ch in instrument_id) % 100 + 50  # pseudo hash
        return [float(base + i) for i in range(40)]

    # ------------------------------------------------------------------
    def run(self, instrument_id: str) -> Dict[str, Any]:  # noqa: D401
        cfg = TrendRidingConfig(instrument_id=instrument_id)
        strat = TrendRidingStrategy(cfg)

        eng_mgr = EngineManager()
        data_mgr = DataManager()

        engine = eng_mgr.create_engine()
        eng_mgr.setup_venue(engine)

        instrument = data_mgr.get_instrument(instrument_id)
        eng_mgr.add_instrument(engine, instrument)

        prices = data_mgr.get_quote_ticks(instrument_id)
        eng_mgr.add_data(engine, prices)

        eng_mgr.add_strategy(engine, strat)
        eng_mgr.run_backtest(engine)
        result = eng_mgr.get_results(engine)

        eng_mgr.cleanup()
        return {"instrument_id": instrument_id, **result}


__all__ = ["TrendRidingBacktestRunner"] 