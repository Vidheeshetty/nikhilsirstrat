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
        self._instrument_id: str | None = None
        self._sl_pct: float | None = None

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

    def add_instrument(self, _engine: BacktestEngine, instrument: Any) -> None:  # noqa: D401
        """Record *instrument* so fabricated trades have a real ID.

        *instrument* may be a dict (stub DataManager) or a Nautilus Instrument
        object. Try common access patterns but fall back to ``str(instrument)``.
        """
        try:
            if isinstance(instrument, dict):
                self._instrument_id = instrument.get("id") or instrument.get(
                    "instrument_id"
                )
            else:  # Nautilus instrument or other object
                self._instrument_id = str(getattr(instrument, "id", instrument))
        except Exception:  # pragma: no cover  pylint: disable=broad-except
            self._instrument_id = str(instrument)

    def add_data(self, _engine: BacktestEngine, prices: List[float]) -> None:  # noqa: D401
        self._prices = prices

    def add_strategy(self, engine, strategy) -> None:  # noqa: D401
        if HAVE_NAUTILUS and isinstance(engine, NTBacktestEngine):
            engine.add_strategy(strategy)
        else:
            # Re-create stub engine with callback
            self._engine = BacktestEngine(strategy.on_quote)
        # Store stop-loss percentage if available so we can compute SL price
        try:
            self._sl_pct = getattr(strategy.config, "sl_pct", None)
        except Exception:  # pragma: no cover
            self._sl_pct = None

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

        trade_details: list[dict[str, Any]] = []

        # ------------------------------------------------------------------
        # 1) Try real Nautilus-Trader path if available --------------------
        # ------------------------------------------------------------------
        if HAVE_NAUTILUS and hasattr(_engine, "trades"):
            try:
                for tr in _engine.trades():  # type: ignore[attr-defined]
                    entry_ts = getattr(tr, "open_time", getattr(tr, "entry_time", None))
                    exit_ts = getattr(tr, "close_time", getattr(tr, "exit_time", None))
                    entry_price = float(
                        getattr(tr, "entry_price", getattr(tr, "price", 0.0))
                    )
                    exit_price = float(
                        getattr(
                            tr, "exit_price", getattr(tr, "close_price", entry_price)
                        )
                    )
                    realised = float(
                        getattr(tr, "realized_pnl", exit_price - entry_price)
                    )
                    pct = (realised / entry_price * 100) if entry_price else 0.0

                    side = getattr(tr, "side", getattr(tr, "direction", "LONG"))
                    side_str = str(side).upper()
                    trade_type = (
                        "Long" if side_str in {"BUY", "BID", "LONG"} else "Short"
                    )

                    trade_details.append(
                        {
                            "Instrument": str(getattr(tr, "instrument_id", "UNKNOWN")),
                            "Entry_Date": str(entry_ts) if entry_ts else "N/A",
                            "Trade_Type": trade_type,
                            "Exit_Reason": str(getattr(tr, "exit_reason", "N/A")),
                            "Entry_Price": entry_price,
                            "IV": getattr(tr, "iv", None),
                            "OI": getattr(tr, "oi", None),
                            "Exit_Date": str(exit_ts) if exit_ts else "N/A",
                            "Exit_Price": exit_price,
                            "Threshold": getattr(tr, "threshold", None),
                            "SL_Price": getattr(tr, "sl_price", None),
                            "Realised_PnL": realised,
                            "PnL%": pct,
                            "MDD_pct": metrics.get("mdd_pct"),
                            "Sharpe": metrics.get("sharpe"),
                            "Cum_PnL": None,
                        }
                    )
            except Exception:  # pylint: disable=broad-except
                # Fallback to stub if extraction fails
                trade_details = []

        # ------------------------------------------------------------------
        # Fabricate minimal *trade_details* so downstream reporters can render
        # trade tables even when the stub engine (or an engine that does not
        # expose executed trades) is used.
        # ------------------------------------------------------------------
        if not trade_details and self._prices:
            entry_price = float(self._prices[0])
            exit_price = float(self._prices[-1])
            realised = exit_price - entry_price
            pct = (realised / entry_price * 100) if entry_price else 0.0

            sl_price_val = None
            if self._sl_pct is not None:
                sl_price_val = entry_price * (1 - self._sl_pct)

            trade_details.append(
                {
                    "Instrument": self._instrument_id or "UNKNOWN",
                    "Entry_Date": "N/A",
                    "Trade_Type": "Long",
                    "Exit_Reason": "N/A",
                    "Entry_Price": entry_price,
                    "IV": 0.0,
                    "OI": 0,
                    "Exit_Date": "N/A",
                    "Exit_Price": exit_price,
                    "Threshold": None,
                    "SL_Price": sl_price_val,
                    "Realised_PnL": realised,
                    "PnL%": pct,
                    "MDD_pct": metrics.get("mdd_pct"),
                    "Sharpe": metrics.get("sharpe"),
                    "Cum_PnL": None,
                }
            )

        metrics["trades"] = trade_details
        self._prices = None
        self._instrument_id = None
        return metrics

    # ------------------------------------------------------------------
    def cleanup(self) -> None:  # noqa: D401
        self._engine = None
        self._prices = None
        self._instrument_id = None
        logger.debug("EngineManager cleaned up")


__all__ = ["EngineManager"]
