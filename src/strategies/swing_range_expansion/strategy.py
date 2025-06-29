from __future__ import annotations

"""Core Swing Range Expansion trading logic (pure Python, no I/O)."""

import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any

from .config import SwingRangeConfig


@dataclass
class TradeRecord:  # pylint: disable=too-many-instance-attributes
    """Simple struct to hold trade details."""

    instrument: str
    entry_date: str
    trade_type: str  # "Long" | "Short"
    entry_price: float
    exit_date: str
    exit_price: float
    exit_reason: str  # "TP" | "SL" | "TIME"
    target_price: float
    stop_price: float

    def to_dict(self) -> Dict[str, Any]:  # noqa: D401
        return {
            "Instrument": self.instrument,
            "Entry_Date": self.entry_date,
            "Trade_Type": self.trade_type,
            "Exit_Reason": self.exit_reason,
            "Entry_Price": round(self.entry_price, 2),
            "Exit_Date": self.exit_date,
            "Exit_Price": round(self.exit_price, 2),
            "Threshold": self.entry_price,  # breakout level
            "SL_Price": round(self.stop_price, 2),
            "Realised_PnL": round(self.exit_price - self.entry_price, 2),
            "PnL%": round(
                (self.exit_price - self.entry_price) / self.entry_price * 100, 2
            ),
            "Cum_PnL": None,  # filled by enrich_trades later
        }


class SwingRangeExpansionStrategy:  # pylint: disable=too-few-public-methods
    """Detect NR7 days and trade breakout next day with R-multiple exits."""

    def __init__(self, config: SwingRangeConfig):
        self.config = config

    # ------------------------------------------------------------------
    @staticmethod
    def _nr7_mask(high: pd.Series, low: pd.Series, lookback: int) -> pd.Series:  # noqa: D401
        """Return boolean Series where each True marks an NR*lookback* day."""
        ranges = high - low
        rolling_min = ranges.rolling(window=lookback, min_periods=lookback).min()
        # NR day is when today's range equals rolling minimum of last lookback days
        return (ranges == rolling_min) & (~rolling_min.isna())

    # ------------------------------------------------------------------
    def generate_trades(
        self, bars: pd.DataFrame, instrument_id: str
    ) -> List[Dict[str, Any]]:  # noqa: D401
        """Run strategy over *bars* DataFrame and return list of trade dicts."""
        if bars.empty:
            return []

        bars = bars.copy().reset_index(drop=True)
        # Ensure required columns exist; fallback to Close-only bars ----------
        if not {"high", "low"}.issubset(bars.columns):
            # Create pseudo high/low columns (±0.25% of close) ----------------
            bars["high"] = bars["close"] * 1.0025
            bars["low"] = bars["close"] * 0.9975
        if "date" not in bars.columns:
            bars["date"] = pd.RangeIndex(len(bars))  # monotonic placeholder

        trades: List[TradeRecord] = []
        open_index: int | None = None
        long_short: str | None = None
        entry_price = target_price = stop_price = 0.0
        range_val = 0.0

        nr_mask = self._nr7_mask(bars["high"], bars["low"], self.config.nr_lookback)

        for i in range(1, len(bars)):
            cur = bars.iloc[i]
            prev = bars.iloc[i - 1]

            # If in position – manage exit conditions ----------------------
            if open_index is not None:
                # update stop/target check on current bar
                if long_short == "Long":
                    # SL first to mimic real market risk management --------
                    if cur["low"] <= stop_price:
                        exit_px = stop_price
                        exit_reason = "SL"
                    elif cur["high"] >= target_price:
                        exit_px = target_price
                        exit_reason = "TP"
                    elif i - open_index >= self.config.max_bars_in_trade:
                        exit_px = cur["close"]
                        exit_reason = "TIME"
                    else:
                        continue  # still in trade
                else:  # Short
                    if cur["high"] >= stop_price:
                        exit_px = stop_price
                        exit_reason = "SL"
                    elif cur["low"] <= target_price:
                        exit_px = target_price
                        exit_reason = "TP"
                    elif i - open_index >= self.config.max_bars_in_trade:
                        exit_px = cur["close"]
                        exit_reason = "TIME"
                    else:
                        continue

                # Record trade -------------------------------------------
                trade = TradeRecord(
                    instrument=instrument_id,
                    entry_date=str(bars.iloc[open_index]["date"]),
                    trade_type=long_short,
                    entry_price=entry_price,
                    exit_date=str(cur["date"]),
                    exit_price=exit_px,
                    exit_reason=exit_reason,
                    target_price=target_price,
                    stop_price=stop_price,
                )
                trades.append(trade)
                # Reset position state ----------------------------------
                open_index = None
                long_short = None
                continue

            # If flat, check for NR day and breakout ----------------------
            if nr_mask.iloc[i - 1]:
                range_val = prev["high"] - prev["low"]
                if range_val == 0:
                    continue  # skip zero-range anomalies
                breakout_high = prev["high"]
                breakout_low = prev["low"]

                # Breakout LONG ---------------------------------------
                if cur["high"] > breakout_high:
                    long_short = "Long"
                    entry_price = breakout_high
                    target_price = entry_price + self.config.target_rr * range_val
                    stop_price = entry_price - self.config.stop_rr * range_val
                    open_index = i
                    continue

                # Breakout SHORT --------------------------------------
                if cur["low"] < breakout_low:
                    long_short = "Short"
                    entry_price = breakout_low
                    target_price = entry_price - self.config.target_rr * range_val
                    stop_price = entry_price + self.config.stop_rr * range_val
                    open_index = i
                    continue

        return [t.to_dict() for t in trades]


__all__ = ["SwingRangeExpansionStrategy"]
