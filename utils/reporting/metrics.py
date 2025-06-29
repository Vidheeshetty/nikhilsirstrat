from __future__ import annotations

import pandas as pd

"""Metrics computation for trade enrichment.

This module provides utilities to compute derived metrics from trade data,
including win/loss classification, cumulative PnL, and other performance
indicators used in backtesting reports.
"""


def enrich_trades(df: pd.DataFrame) -> pd.DataFrame:  # noqa: D401
    """Return *df* with additional columns calculated on the fly.

    Adds / overwrites:
    • PnL%         – percentage return per trade.
    • Cum_PnL      – cumulative realised PnL per instrument_id (ordered by exit date).
    • is_win       – boolean flag (Realised_PnL > 0).
    """

    if df.empty:
        return df

    out = df.copy()

    # ------------------------------------------------------------------
    # Ensure numeric columns are truly numeric for math operations
    # ------------------------------------------------------------------
    for col in ["Realised_PnL", "Entry_Price", "Exit_Price"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # ------------------------------------------------------------------
    # PnL % per trade (if missing or NaN)
    # ------------------------------------------------------------------
    if "PnL%" not in out.columns:
        out["PnL%"] = None
    mask_missing_pct = out["PnL%"].isna()
    out.loc[mask_missing_pct, "PnL%"] = (
        (
            out.loc[mask_missing_pct, "Realised_PnL"]
            / out.loc[mask_missing_pct, "Entry_Price"]
        )
        * 100
    ).round(2)

    # Win/Loss label ----------------------------------------------------
    out["Win/Loss"] = out["Realised_PnL"].apply(
        lambda x: "Win" if x > 0 else ("Loss" if x < 0 else "Flat")
    )
    out["is_win"] = out["Win/Loss"] == "Win"

    # ------------------------------------------------------------------
    # Cumulative PnL across *all* trades (chronological)
    # ------------------------------------------------------------------
    out["Cum_PnL"] = (
        out.sort_values(["Exit_Date", "Entry_Date"], na_position="last")["Realised_PnL"]
        .cumsum()
        .round(2)
    )

    return out


__all__ = ["enrich_trades"]
