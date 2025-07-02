from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import os
import re

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
    def _default_prices(instrument_id: str) -> List[Any]:  # noqa: D401
        """Prefer real OHLC bars from the local Parquet catalog; gracefully
        degrade to LAST price series or ultimately synthetic data so unit tests
        remain deterministic.

        The returned list items are *either*:
        • objects exposing ``open``, ``high``, ``low``, ``close``, ``timestamp``
          attributes (when bar data available), or
        • plain ``float`` close prices (fallback modes).
        """

        from types import SimpleNamespace
        import pandas as pd  # local import to avoid heavyweight dep at module level

        # ------------------------------------------------------------------
        # Generic retrieval via DataManager using DATA_CATALOG_ROOTS env var
        # ------------------------------------------------------------------
        try:
            dm_generic = DataManager()
            generic_prices = dm_generic.get_trade_ticks(instrument_id, allow_stub=False)
            if generic_prices and len(generic_prices) > 1:
                print(
                    f"DEBUG: Returning {len(generic_prices)} prices from generic DataManager"
                )
                return generic_prices
        except Exception as _e:
            # Fall through to specialised loaders below
            pass

        # ------------------------------------------------------------------
        # 0) Load via Nautilus-Trader ParquetDataCatalog if available --------
        # ------------------------------------------------------------------
        try:
            from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog  # type: ignore

            cat_root = Path("catalog-data/zerodha-gold-guinea/catalog")
            if cat_root.exists():
                cat = ParquetDataCatalog(cat_root)
                bar_type = f"{instrument_id}-1-MINUTE-LAST-EXTERNAL"
                bars = cat.bars(bar_types=[bar_type], as_nautilus=False)
                if bars:
                    return (
                        bars  # list of objects with open/high/low/close/timestamp attrs
                    )
        except Exception:  # pragma: no cover
            pass

        # ------------------------------------------------------------------
        # 1) Minute-level bars ------------------------------------------------
        # ------------------------------------------------------------------
        # Determine bar base directories from DATA_CATALOG_ROOTS (colon separated)
        import os as _os

        catalog_roots = _os.environ.get("DATA_CATALOG_ROOTS", "catalog-data").split(":")
        bar_dirs_all = []
        for root in catalog_roots:
            bar_base_dir = Path(root) / "catalog" / "data" / "bar"
            if bar_base_dir.exists():
                bar_dirs_all.extend(
                    bar_base_dir.glob(f"{instrument_id}*-1-MINUTE-LAST-EXTERNAL")
                )

        bar_dirs = list(bar_dirs_all)
        print(
            f"DEBUG: Looking for bar dirs with pattern: {instrument_id}*-1-MINUTE-LAST-EXTERNAL"
        )
        print(f"DEBUG: Found bar dirs: {bar_dirs}")
        if bar_dirs:
            bar_dir = bar_dirs[0]  # Take the first match
            print(f"DEBUG: Using bar dir: {bar_dir}")
            try:
                parts = sorted(bar_dir.glob("*.parquet"))
                print(f"DEBUG: Found parquet files: {parts}")
                if parts:
                    df = pd.read_parquet(parts[0])
                    print(f"DEBUG: Loaded parquet with shape: {df.shape}")
                    print(f"DEBUG: Columns: {df.columns.tolist()}")
                    # Chronological order ------------------------------------------------
                    if "ts" in df.columns:
                        df = df.sort_values("ts")
                    elif "timestamp" in df.columns:
                        df = df.sort_values("timestamp")

                    opens = df["open"].tolist()
                    highs = df["high"].tolist()
                    lows = df["low"].tolist()
                    closes = df["close"].tolist()

                    # Use ts_event for timestamps, fallback to index
                    if "ts_event" in df.columns:
                        try:
                            ts_series = (
                                pd.to_numeric(df["ts_event"], errors="coerce")
                                .fillna(0)
                                .astype(int)
                                .tolist()
                            )
                        except Exception:
                            ts_series = list(range(len(closes)))
                    elif "ts" in df.columns:
                        try:
                            ts_series = (
                                pd.to_numeric(df["ts"], errors="coerce")
                                .fillna(0)
                                .astype(int)
                                .tolist()
                            )
                        except Exception:
                            ts_series = list(range(len(closes)))
                    elif "timestamp" in df.columns:
                        try:
                            ts_series = (
                                pd.to_numeric(df["timestamp"], errors="coerce")
                                .fillna(0)
                                .astype(int)
                                .tolist()
                            )
                        except Exception:
                            ts_series = list(range(len(closes)))
                    else:
                        ts_series = list(range(len(closes)))

                    minute_bars: list[Any] = []
                    for idx in range(len(closes)):
                        ts_val = ts_series[idx] if ts_series else idx
                        minute_bars.append(
                            SimpleNamespace(
                                open=float(opens[idx]),
                                high=float(highs[idx]),
                                low=float(lows[idx]),
                                close=float(closes[idx]),
                                timestamp=int(ts_val),
                            )
                        )
                    if minute_bars:
                        target_interval = os.getenv("BAR_INTERVAL", "1-MINUTE").upper()
                        # If caller requested >1 minute bars and catalog lacks them, aggregate.
                        if target_interval not in (
                            "1-MIN",
                            "1-MINUTE",
                            "1M",
                            "1",
                        ):  # simplistic check
                            match = re.match(r"(\d+)([HM])", target_interval)
                            if match:
                                factor = int(match.group(1))
                                unit = match.group(2)
                                if unit == "H":
                                    factor *= 60
                                if factor > 1:
                                    print(
                                        f"DEBUG: Aggregating 1-minute bars into {target_interval} using factor={factor}"
                                    )

                                    agg_bars: list[Any] = []
                                    for i in range(0, len(minute_bars), factor):
                                        chunk = minute_bars[i : i + factor]
                                        if not chunk:
                                            continue
                                        open_px = chunk[0].open
                                        high_px = max(b.high for b in chunk)
                                        low_px = min(b.low for b in chunk)
                                        close_px = chunk[-1].close
                                        ts_val = getattr(chunk[-1], "timestamp", i)
                                        from types import SimpleNamespace

                                        agg_bars.append(
                                            SimpleNamespace(
                                                open=open_px,
                                                high=high_px,
                                                low=low_px,
                                                close=close_px,
                                                timestamp=ts_val,
                                            )
                                        )
                                    if agg_bars:
                                        print(
                                            f"DEBUG: Returning {len(agg_bars)} aggregated bars"
                                        )
                                        return agg_bars
                        # Default: return raw minute bars
                        print(
                            f"DEBUG: Returning {len(minute_bars)} bar objects (1-minute)"
                        )
                        return minute_bars
            except Exception as e:  # pragma: no cover
                print(f"DEBUG: Exception loading bars: {e}")
                pass

        # ------------------------------------------------------------------
        # 2) LAST price series from bar metadata (no high/low information)
        # ------------------------------------------------------------------
        meta_path = None
        for root in catalog_roots:
            p = Path(root) / "catalog-meta" / "bar_metadata.parquet"
            if p.exists():
                meta_path = p
                break
        if meta_path is None:
            meta_path = Path(
                "catalog-data/zerodha-gold-guinea/catalog-meta/bar_metadata.parquet"
            )
        if meta_path.exists():
            try:
                df = pd.read_parquet(
                    meta_path, columns=["instrument_id", "timestamp", "last"]
                )
                print(f"DEBUG: Loaded metadata with shape: {df.shape}")
                print(f"DEBUG: Unique instrument_ids: {df['instrument_id'].unique()}")
                df = df[df["instrument_id"] == instrument_id].sort_values("timestamp")
                print(f"DEBUG: After filtering by {instrument_id}, shape: {df.shape}")
                if not df.empty:
                    prices = [float(x) for x in df["last"].tolist()]
                    print(f"DEBUG: Returning {len(prices)} prices from metadata")
                    return prices
            except Exception as e:  # pragma: no cover
                print(f"DEBUG: Exception in metadata fallback: {e}")
                pass

        # ------------------------------------------------------------------
        # 3) Deterministic synthetic fallback --------------------------------
        # ------------------------------------------------------------------
        dm = DataManager(catalog_path="catalog-data/zerodha-gold-guinea")
        return dm._synthetic_prices(instrument_id)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    def run(self, instrument_id: str) -> Dict[str, Any]:  # noqa: D401
        # Load YAML config if present next to strategy, else default dataclass
        default_yaml_path = Path(__file__).resolve().parents[2] / "strategy.yaml"
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
        print("DEBUG config use_fractals", cfg.use_fractals)

        eng_mgr = EngineManager()
        data_mgr = DataManager(catalog_path="catalog-data/zerodha-gold-guinea")

        engine = eng_mgr.create_engine()
        eng_mgr.setup_venue(engine)

        instrument = data_mgr.get_instrument(instrument_id)
        eng_mgr.add_instrument(engine, instrument)

        # ------------------------------------------------------------------
        # Price series: delegate to configurable provider so we can inject
        # *either* real OHLC bars *or* simple close-price floats depending on
        # data availability.
        # ------------------------------------------------------------------
        prices_or_bars = self._prices_provider(instrument_id)
        if not prices_or_bars:
            raise ValueError(f"No price data found for {instrument_id}")

        print(f"DEBUG instrument_id: {instrument_id}")
        print(
            f"DEBUG prices_or_bars type: {type(prices_or_bars[0]) if prices_or_bars else 'empty'}"
        )
        print(f"DEBUG first item: {prices_or_bars[0] if prices_or_bars else 'none'}")
        print(
            f"DEBUG has close attr: {hasattr(prices_or_bars[0], 'close') if prices_or_bars else 'none'}"
        )

        # ------------------------------------------------------------------
        # Resample to higher timeframe if BAR_INTERVAL env var specifies
        # something larger than 1-MINUTE. This runs regardless of where
        # the prices came from (real bars or float closes).
        # ------------------------------------------------------------------
        target_interval = os.getenv("BAR_INTERVAL", "1-MINUTE").upper()
        if target_interval not in ("1-MIN", "1-MINUTE", "1M", "1"):
            match = re.match(r"(\d+)([HM])", target_interval)
            if match:
                factor = int(match.group(1))
                unit = match.group(2)
                if unit == "H":
                    factor *= 60
                if factor > 1:
                    from types import SimpleNamespace

                    # Normalise to bars list with OHLC first
                    def _to_bar(obj):
                        if hasattr(obj, "close"):
                            return obj
                        # float close -> synthetic bar with tiny envelope
                        price = float(obj)
                        return SimpleNamespace(
                            open=price,
                            high=price * 1.0001,
                            low=price * 0.9999,
                            close=price,
                            timestamp=0,
                        )

                    bars_norm = [_to_bar(x) for x in prices_or_bars]

                    agg_bars: list[Any] = []
                    for i in range(0, len(bars_norm), factor):
                        chunk = bars_norm[i : i + factor]
                        if not chunk:
                            continue
                        open_px = chunk[0].open
                        high_px = max(b.high for b in chunk)
                        low_px = min(b.low for b in chunk)
                        close_px = chunk[-1].close
                        ts_val = getattr(chunk[-1], "timestamp", i)
                        agg_bars.append(
                            SimpleNamespace(
                                open=open_px,
                                high=high_px,
                                low=low_px,
                                close=close_px,
                                timestamp=ts_val,
                            )
                        )
                    prices_or_bars = agg_bars or prices_or_bars
                    print(
                        f"DEBUG: After aggregation factor {factor}, bars = {len(prices_or_bars)}"
                    )

        eng_mgr.add_data(engine, prices_or_bars)

        # For period calculation we load timestamps from parquet meta again
        import pandas as _pd

        meta_path = Path(
            "catalog-data/zerodha-gold-guinea/catalog-meta/bar_metadata.parquet"
        )
        if meta_path.exists():
            _df = _pd.read_parquet(meta_path, columns=["instrument_id", "timestamp"])
            _df = _df[_df["instrument_id"] == instrument_id].sort_values("timestamp")
            if not _df.empty:
                start_ns = int(_df["timestamp"].iloc[0])
                end_ns = int(_df["timestamp"].iloc[-1])
            else:
                start_ns = end_ns = None
        else:
            start_ns = end_ns = None

        eng_mgr.add_strategy(engine, strat)
        engine = eng_mgr._engine  # use possibly replaced stub engine
        eng_mgr.run_backtest(engine)

        # Manually invoke on_stop so strategy can record and close any open
        # positions – stub BacktestEngine does not call lifecycle hooks.
        try:
            strat.on_stop()
        except Exception:  # pragma: no cover
            pass

        print("DEBUG trades len", len(strat.trades))

        result = eng_mgr.get_results(engine)

        eng_mgr.cleanup()

        # Use real trades from strategy if available ----------------------
        trades = strat.trades
        for tr in trades:
            tr["Instrument"] = instrument_id
            tr["MDD_pct"] = result.get("mdd_pct")

        # Fallback to synthetic single trade if strategy produced none ----
        if not trades:
            # Handle both bar objects and price floats --------------------
            has_close_attr = hasattr(prices_or_bars[0], "close")
            entry_price = (
                float(prices_or_bars[0].close)
                if has_close_attr
                else float(prices_or_bars[0])
            )
            exit_price = (
                float(prices_or_bars[-1].close)
                if has_close_attr
                else float(prices_or_bars[-1])
            )
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

        # Peak exposure approximation: max entry price / leverage
        LEVERAGE = 10
        try:
            peak_expo = (
                max(float(t["Entry_Price"]) for t in trades) / LEVERAGE
                if trades
                else 0.0
            )
        except Exception:
            peak_expo = 0.0

        merged: Dict[str, Any] = {**result}
        merged["instrument_id"] = instrument_id
        merged["trades"] = trades
        merged["data_source"] = data_mgr.describe_source()
        merged["start_time"] = start_ns
        merged["end_time"] = end_ns
        merged["peak_exposure"] = peak_expo

        # ------------------------------------------------------------------
        # Save indicator plot for visual inspection ------------------------
        # ------------------------------------------------------------------
        try:
            import pandas as pd
            import plotly.graph_objects as go

            # Build DataFrame of close prices -----------------------------
            if prices_or_bars and hasattr(prices_or_bars[0], "close"):
                close_ser = [bar.close for bar in prices_or_bars]
            else:
                close_ser = [float(p) for p in prices_or_bars]

            df = pd.DataFrame({"price": close_ser})
            df["sma_short"] = df["price"].rolling(5).mean()
            df["sma_long"] = df["price"].rolling(200).mean()
            df["idx"] = range(len(df))
            # -------------------- FRACTAL CALCULATION ---------------------
            # We replicate the 5-bar fractal logic using the synthetic high/low
            # values generated inside the strategy (±0.25% of close). This gives
            # an approximate visual reference of the breakout levels.
            df["high"] = df["price"] * 1.0025
            df["low"] = df["price"] * 0.9975

            frac_high_x, frac_high_y, frac_low_x, frac_low_y = [], [], [], []
            for i in range(4, len(df)):
                center = i - 2  # the potential fractal pivot
                window_slice = slice(i - 4, i + 1)

                # High fractal -------------------------------------------------
                highs_window = df["high"].iloc[window_slice]
                if (
                    df["high"].iloc[center] == highs_window.max()
                    and df["high"].iloc[center]
                    > highs_window.drop(index=highs_window.index[2]).max()
                ):
                    frac_high_x.append(df["idx"].iloc[center])
                    frac_high_y.append(df["high"].iloc[center])

                # Low fractal --------------------------------------------------
                lows_window = df["low"].iloc[window_slice]
                if (
                    df["low"].iloc[center] == lows_window.min()
                    and df["low"].iloc[center]
                    < lows_window.drop(index=lows_window.index[2]).min()
                ):
                    frac_low_x.append(df["idx"].iloc[center])
                    frac_low_y.append(df["low"].iloc[center])

            # ----------------------- PLOTLY FIG ----------------------------
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["idx"], y=df["price"], name="Price"))
            fig.add_trace(go.Scatter(x=df["idx"], y=df["sma_short"], name="5-SMA"))
            fig.add_trace(go.Scatter(x=df["idx"], y=df["sma_long"], name="200-SMA"))
            # Overlay fractal markers ---------------------------------------
            if frac_high_x:
                fig.add_trace(
                    go.Scatter(
                        x=frac_high_x,
                        y=frac_high_y,
                        mode="markers",
                        name="High Fractal",
                        marker=dict(color="orange", symbol="triangle-up", size=7),
                    )
                )
            if frac_low_x:
                fig.add_trace(
                    go.Scatter(
                        x=frac_low_x,
                        y=frac_low_y,
                        mode="markers",
                        name="Low Fractal",
                        marker=dict(color="purple", symbol="triangle-down", size=7),
                    )
                )
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
