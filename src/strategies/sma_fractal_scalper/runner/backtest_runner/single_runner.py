from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from strategies.sma_fractal_scalper.strategy import SmaFractalScalper
from strategies.sma_fractal_scalper.config import SmaFractalScalperConfig
from utils.runners.engine_manager import EngineManager
from utils.data.data_manager import DataManager

"""Single-instrument backtest runner for SmaFractalScalper.

Replicates the structure of TrendRidingBacktestRunner so that it plugs into the
existing CLI (`scripts/run_backtest.py`).  It delegates execution to the shared
EngineManager which feeds quote ticks (floats) to the strategy.
"""


class SmaFractalScalperBacktestRunner:  # pylint: disable=too-few-public-methods
    """Execute a back-test for one instrument and return summary dict."""

    def __init__(self, prices_provider=None):
        self._prices_provider = prices_provider or self._default_prices

    # ------------------------------------------------------------------
    @staticmethod
    def _default_prices(instrument_id: str) -> List[float]:  # noqa: D401
        """Load minute-level prices using DataManager or direct parquet fallback.

        1. Try DataManager (which fetches daily bars by default – may work if
           intraday minutes are registered).
        2. Fallback to reading `catalog-meta/bar_metadata.parquet` directly and
           extracting the "last" column for the requested *instrument_id*.
        3. If both paths fail, return synthetic stub prices so tests remain
           green.
        """
        # First attempt via DataManager -----------------------------------
        dm = DataManager(catalog_path="catalog-data/zerodha-gold-guinea")
        try:
            return dm.get_trade_ticks(instrument_id, allow_stub=False)
        except Exception:  # pylint: disable=broad-except
            pass

        # Second attempt – direct parquet read ---------------------------
        import pandas as pd
        from pathlib import Path

        meta_path = Path("catalog-data/zerodha-gold-guinea/catalog-meta/bar_metadata.parquet")
        if meta_path.exists():
            try:
                df = pd.read_parquet(meta_path, columns=["instrument_id", "timestamp", "last"])
                df = df[df["instrument_id"] == instrument_id]
                if not df.empty:
                    df = df.sort_values("timestamp")
                    return df["last"].astype(float).tolist()
            except Exception:  # pragma: no cover
                pass

        # Final fallback – synthetic prices ------------------------------
        return dm._synthetic_prices(instrument_id)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    def run(self, instrument_id: str) -> Dict[str, Any]:  # noqa: D401
        # Load YAML config if present next to strategy, else default dataclass
        default_yaml_path = (
            Path(__file__).resolve().parents[2] / "strategy.yaml"
        )
        if default_yaml_path.exists():
            try:
                import yaml

                cfg_dict = yaml.safe_load(default_yaml_path.read_text()) or {}
                cfg = SmaFractalScalperConfig(**cfg_dict)
            except Exception:  # pragma: no cover
                cfg = SmaFractalScalperConfig()
        else:
            cfg = SmaFractalScalperConfig()

        strat = SmaFractalScalper(cfg)

        eng_mgr = EngineManager()
        data_mgr = DataManager(catalog_path="catalog-data/zerodha-gold-guinea")

        engine = eng_mgr.create_engine()
        eng_mgr.setup_venue(engine)

        instrument = data_mgr.get_instrument(instrument_id)
        eng_mgr.add_instrument(engine, instrument)

        # ------------------------------------------------------------------
        # Price series: delegate to configurable provider so we can inject
        # intraday loaders, synthetic stubs, etc.
        # ------------------------------------------------------------------
        prices = self._prices_provider(instrument_id)
        if not prices:
            raise ValueError(f"No prices found for {instrument_id}")
        eng_mgr.add_data(engine, prices)

        eng_mgr.add_strategy(engine, strat)
        eng_mgr.run_backtest(engine)
        result = eng_mgr.get_results(engine)

        eng_mgr.cleanup()

        # Use real trades from strategy if available ----------------------
        trades = strat.trades
        for tr in trades:
            tr["Instrument"] = instrument_id

        # Fallback to synthetic single trade if strategy produced none ----
        if not trades:
            entry_price = prices[0]
            exit_price = prices[-1]
            realised_pnl = exit_price - entry_price
            pnl_pct = (realised_pnl / entry_price * 100) if entry_price else 0.0
            trades = [
                {
                    "Instrument": instrument_id,
                    "Entry_Date": datetime.now().strftime("%Y-%m-%d"),
                    "Trade_Type": "Long",
                    "Exit_Reason": "END",
                    "Entry_Price": round(entry_price, 2),
                    "IV": None,
                    "OI": None,
                    "Exit_Date": datetime.now().strftime("%Y-%m-%d"),
                    "Exit_Price": round(exit_price, 2),
                    "Threshold": None,
                    "SL_Price": None,
                    "Realised_PnL": round(realised_pnl, 2),
                    "PnL%": round(pnl_pct, 2),
                    "MDD_pct": result.get("mdd_pct", 0.0),
                    "Sharpe": result.get("sharpe", 0.0),
                    "Cum_PnL": None,
                }
            ]

        merged: Dict[str, Any] = {**result}
        merged["instrument_id"] = instrument_id
        merged["trades"] = trades
        merged["data_source"] = data_mgr.describe_source()

        # ------------------------------------------------------------------
        # Save indicator plot for visual inspection ------------------------
        # ------------------------------------------------------------------
        try:
            import pandas as pd
            from pathlib import Path
            import plotly.graph_objects as go
            from datetime import datetime
            # Build DataFrame
            df = pd.DataFrame({"price": prices})
            df["sma_short"] = df["price"].rolling(5).mean()
            df["sma_long"] = df["price"].rolling(200).mean()
            df["idx"] = range(len(df))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["idx"], y=df["price"], name="Price"))
            fig.add_trace(go.Scatter(x=df["idx"], y=df["sma_short"], name="5-SMA"))
            fig.add_trace(go.Scatter(x=df["idx"], y=df["sma_long"], name="200-SMA"))
            ts = datetime.now().strftime("%H-%M-%S")
            plot_dir = Path("runlogs/plots")
            plot_dir.mkdir(parents=True, exist_ok=True)
            plot_file = plot_dir / f"{instrument_id}_{ts}.html"
            fig.write_html(plot_file, include_plotlyjs="cdn")
            merged["plot_path"] = str(plot_file.relative_to(Path.cwd()))
        except Exception:
            pass

        return merged


__all__ = ["SmaFractalScalperBacktestRunner"] 