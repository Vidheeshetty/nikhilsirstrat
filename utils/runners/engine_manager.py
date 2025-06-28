from __future__ import annotations

"""EngineManager – lightweight wrapper around the in-memory BacktestEngine.

Acts as an adapter so strategy code can later switch to Nautilus-Trader without
changing the orchestrator & batch-runner layers.
"""

from typing import Any, List
import logging

# Try to import Nautilus-Trader; fall back to stub if unavailable ----------------
try:
    from nautilus_trader.backtest.engine import BacktestEngine as NTBacktestEngine  # type: ignore
    from nautilus_trader.test_kit.stubs.venue import create_venue_config  # type: ignore
    from nautilus_trader.model.identifiers import Venue  # type: ignore
    HAVE_NAUTILUS = True
except Exception:  # pragma: no cover  pylint: disable=broad-except
    HAVE_NAUTILUS = False
    NTBacktestEngine = None  # type: ignore

from strategies.trend_riding.runner.backtest_runner.engine import BacktestEngine  # stub
from utils.runners.metrics import calculate_metrics

logger = logging.getLogger(__name__)


class EngineManager:  # pylint: disable=too-few-public-methods
    """Manage a single BacktestEngine lifecycle."""

    def __init__(self):
        self._engine: BacktestEngine | None = None
        self._prices: List[float] | None = None

    # ------------------------------------------------------------------
    def create_engine(self) -> BacktestEngine:  # noqa: D401
        if self._engine is not None:
            raise RuntimeError("Engine already created – call cleanup() first")
        # Decide engine implementation --------------------------------------
        if HAVE_NAUTILUS:
            try:
                venue_cfg = create_venue_config(Venue("SIM"))
                self._engine = NTBacktestEngine(venue_cfg)
                return self._engine
            except Exception:  # pragma: no cover  pylint: disable=broad-except
                # Fall back to stub if Nautilus init fails (e.g., missing deps)
                pass
        # Stub engine executes `on_quote(price)` for supplied price series.
        self._engine = BacktestEngine(lambda *_: None)
        return self._engine

    # The following methods are *no-ops* for the stub, but we expose them so
    # callers don't need to special-case when we swap in the real engine.
    # ------------------------------------------------------------------
    def setup_venue(self, _engine: BacktestEngine) -> None:  # noqa: D401
        pass

    def add_instrument(self, _engine: BacktestEngine, _instrument: Any) -> None:  # noqa: D401
        pass

    def add_data(self, _engine: BacktestEngine, prices: List[float]) -> None:  # noqa: D401
        self._prices = prices

    def add_strategy(self, engine, strategy) -> None:  # noqa: D401
        if HAVE_NAUTILUS and isinstance(engine, NTBacktestEngine):
            engine.add_strategy(strategy)
        else:
            # Re-create stub engine with callback
            self._engine = BacktestEngine(strategy.on_quote)

    # ------------------------------------------------------------------
    def run_backtest(self, engine: BacktestEngine) -> None:  # noqa: D401
        if HAVE_NAUTILUS and isinstance(engine, NTBacktestEngine):
            engine.run()
        else:
            if self._prices is None:
                raise ValueError("No data added to engine")
            engine.run(self._prices)

    def get_results(self, _engine: BacktestEngine) -> dict[str, Any]:  # noqa: D401
        metrics = calculate_metrics(self._prices or [])
        metrics["num_quotes"] = len(self._prices or [])
        return metrics

    # ------------------------------------------------------------------
    def cleanup(self) -> None:  # noqa: D401
        self._engine = None
        self._prices = None
        logger.debug("EngineManager cleaned up")


__all__ = ["EngineManager"] 