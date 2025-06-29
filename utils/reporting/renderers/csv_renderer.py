from __future__ import annotations

from pathlib import Path
from typing import Any, List, Dict
import pandas as pd
from utils.reporting.metrics import enrich_trades

from .base import Renderer


class CsvTradeRenderer(Renderer):
    """Render trade *details* (not just instrument summary) to CSV.

    If the supplied *results* objects contain a ``trades`` key (as produced by
    ``EngineManager``) the renderer flattens all those trade dictionaries into
    a single table – this matches the historical CSV format used in the legacy
    code-base. If no such key is present we fall back to writing the *results*
    themselves so that existing unit tests remain unaffected.
    """

    def render(self, results: List[Dict[str, Any]], out_path: Path) -> None:  # noqa: D401
        # Flatten trades if available --------------------------------------
        trade_rows: List[Dict[str, Any]] = []
        for res in results:
            trades = res.get("trades")
            if trades:
                trade_rows.extend(trades)
        # Fallback to summary rows if no trade details ----------------------
        rows_to_write = trade_rows if trade_rows else results

        if not rows_to_write:
            # Nothing to write – avoid creating empty file
            return

        df = pd.DataFrame(rows_to_write)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Round float columns to 2 decimals --------------------------------
        float_cols = df.select_dtypes(include=["float", "float64", "float32"]).columns
        df[float_cols] = df[float_cols].round(2)

        if not df.empty and "Realised_PnL" in df.columns:
            df = enrich_trades(df)

        # Replace legacy 'UNKNOWN' placeholders with instrument_id if present
        if "Instrument" in df.columns and (df["Instrument"] == "UNKNOWN").any():
            if "instrument_id" in df.columns:
                df.loc[df["Instrument"] == "UNKNOWN", "Instrument"] = df.loc[
                    df["Instrument"] == "UNKNOWN", "instrument_id"
                ]
            elif "Instrument_ID" in df.columns:
                df.loc[df["Instrument"] == "UNKNOWN", "Instrument"] = df.loc[
                    df["Instrument"] == "UNKNOWN", "Instrument_ID"
                ]

        df.to_csv(out_path, index=False)


__all__ = ["CsvTradeRenderer"]
