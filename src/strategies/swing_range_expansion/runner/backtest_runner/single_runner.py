import pandas as pd
from pathlib import Path
from typing import Dict, Any

from utils.data.data_manager import DataManager
from utils.runners.metrics import calculate_metrics
from utils.reporting.metrics import enrich_trades  # type: ignore

from ...config import SwingRangeConfig
from ...strategy import SwingRangeExpansionStrategy

"""Single backtest runner for Swing Range Expansion strategy."""


class SwingRangeExpansionBacktestRunner:  # pylint: disable=too-few-public-methods
    """High-level orchestration: load bars → run strategy → return summary."""

    def __init__(self, bars_provider=None):
        self._bars_provider = bars_provider or self._default_bars_provider

    # ------------------------------------------------------------------
    @staticmethod
    def _default_bars_provider(instrument_id: str) -> pd.DataFrame:  # noqa: D401
        """Return minimal OHLC bars using DataManager (close-only fallback)."""
        data_mgr = DataManager()
        # Always allow stub prices so the runner works even when the Parquet
        # catalog lacks the requested instrument during early development.
        closes = data_mgr.get_trade_ticks(instrument_id, allow_stub=True)
        df = pd.DataFrame(
            {
                "close": closes,
            }
        )
        # Synthetic OHLC (±0.25% random-ish) ---------------------------------
        df["high"] = df["close"] * 1.0025
        df["low"] = df["close"] * 0.9975
        df["open"] = df["close"].shift(1).fillna(df["close"])
        df["date"] = pd.RangeIndex(len(df))
        return df

    # ------------------------------------------------------------------
    def run(
        self, instrument_id: str, *, cfg_path: str | Path | None = None, **cfg_overrides
    ) -> Dict[str, Any]:  # noqa: D401
        """Execute back-test and return result dict compatible with reporters."""
        # Load config ------------------------------------------------------
        if cfg_path is not None:
            cfg = SwingRangeConfig.from_yaml(
                cfg_path, instrument_id=instrument_id, **cfg_overrides
            )
        else:
            cfg = SwingRangeConfig(instrument_id=instrument_id, **cfg_overrides)
        strat = SwingRangeExpansionStrategy(cfg)

        bars = self._bars_provider(instrument_id)
        trades = strat.generate_trades(bars, instrument_id)

        # Metrics on close prices -----------------------------------------
        metrics = calculate_metrics(bars["close"].tolist())
        metrics["instrument_id"] = instrument_id
        metrics["trades"] = (
            enrich_trades(pd.DataFrame(trades)).to_dict("records") if trades else trades
        )
        metrics["pnl"] = (
            sum(t["Realised_PnL"] for t in trades)
            if trades
            else metrics.get("pnl", 0.0)
        )
        metrics["data_source"] = DataManager().describe_source()

        return metrics


__all__ = ["SwingRangeExpansionBacktestRunner"]
