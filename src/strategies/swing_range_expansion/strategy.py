from __future__ import annotations

import pandas as pd
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from utils.strategy.base_strategy import BaseStrategy
from .config import SwingRangeConfig
from .entry import compute_signal, Direction
from .exit import should_exit
from .risk import RiskManager
from .position import calculate_size

"""Swing Range Expansion Strategy – modular implementation compatible with BaseStrategy."""


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


class SwingRangeExpansionStrategy(BaseStrategy):
    """Detect NR7 days and trade breakout next day with R-multiple exits."""

    config_class = SwingRangeConfig

    def _setup(self) -> None:  # noqa: D401,override
        """Initialize strategy state."""
        self._bars: List[Dict[str, Any]] = []
        self._in_position: bool = False
        self._entry_price: Optional[float] = None
        self._position_side: Optional[Direction] = None
        self._range_val: float = 0.0
        self._entry_index: Optional[int] = None
        self._trades: List[TradeRecord] = []

        self.risk_mgr = RiskManager(self.config.stop_rr, self.config.target_rr)
        super()._setup()

    def on_quote(self, price: float):  # noqa: D401,override – simplified
        """Process a new quote price (float for unit-test simplicity).

        We create OHLC bars from the price feed for compatibility with
        the NR7 breakout logic.
        """
        # Create OHLC bar from price (simplified for testing)
        bar = {
            "open": price,
            "high": price * 1.0025,  # Synthetic high
            "low": price * 0.9975,  # Synthetic low
            "close": price,
            "date": len(self._bars),
        }
        self._bars.append(bar)

        current_index = len(self._bars) - 1

        if current_index < self.config.nr_lookback:
            return  # Not enough data yet

        # Convert to DataFrame for signal computation
        bars_df = pd.DataFrame(self._bars)

        # ------------------------------------------------------------------
        # ENTRY – check for NR breakout
        # ------------------------------------------------------------------
        if not self._in_position:
            direction, entry_price, range_val, _, _ = compute_signal(
                bars_df, current_index, self.config.nr_lookback
            )

            if direction in (Direction.LONG, Direction.SHORT):
                self._enter_trade(entry_price, direction, range_val, current_index)
        else:
            # --------------------------------------------------------------
            # EXIT – check exit conditions
            # --------------------------------------------------------------
            bars_in_trade = current_index - (self._entry_index or 0)
            current_bar = pd.Series(bar)

            should_exit_now, exit_reason, exit_price = should_exit(
                current_bar=current_bar,
                direction=self._position_side or Direction.NONE,
                entry_price=self._entry_price or 0.0,
                range_val=self._range_val,
                target_rr=self.config.target_rr,
                stop_rr=self.config.stop_rr,
                bars_in_trade=bars_in_trade,
                max_bars_in_trade=self.config.max_bars_in_trade,
            )

            if should_exit_now:
                self._exit_trade(exit_price, exit_reason, current_index)

    def _enter_trade(
        self, price: float, direction: Direction, range_val: float, index: int
    ) -> None:
        """Enter a new trade."""
        size = calculate_size(
            capital=100_000,
            risk_per_trade_pct=0.01,
            entry_price=price,
            stop_price=price - (self.config.stop_rr * range_val)
            if direction == Direction.LONG
            else price + (self.config.stop_rr * range_val),
        )

        self.log.info("Entering %s at %.2f, size=%s", direction.name, price, size)
        self._in_position = True
        self._entry_price = price
        self._position_side = direction
        self._range_val = range_val
        self._entry_index = index

    def _exit_trade(self, price: float, reason: str, index: int) -> None:
        """Exit current trade."""
        if not self._in_position or self._entry_price is None:
            return

        # Calculate PnL
        pnl = price - self._entry_price
        if self._position_side == Direction.SHORT:
            pnl = -pnl

        # Create trade record
        stop_price, target_price = self.risk_mgr.get_exit_prices(
            self._entry_price, self._range_val, self._position_side or Direction.NONE
        )

        trade = TradeRecord(
            instrument=self.config.instrument_id,
            entry_date=str(self._entry_index or 0),
            trade_type=self._position_side.value if self._position_side else "UNKNOWN",
            entry_price=self._entry_price,
            exit_date=str(index),
            exit_price=price,
            exit_reason=reason,
            target_price=target_price,
            stop_price=stop_price,
        )
        self._trades.append(trade)

        self.log.info(
            "Exiting %s at %.2f, PnL=%.2f, Reason=%s",
            self._position_side.name if self._position_side else "?",
            price,
            pnl,
            reason,
        )

        # Reset position state
        self._in_position = False
        self._entry_price = None
        self._position_side = None
        self._range_val = 0.0
        self._entry_index = None

    def on_stop(self):  # noqa: D401,override
        """Strategy cleanup."""
        super().on_stop()
        self.log.info(
            "Processed %s bars in total. Generated %s trades.",
            len(self._bars),
            len(self._trades),
        )

    def generate_trades(
        self, bars: pd.DataFrame, instrument_id: str
    ) -> List[Dict[str, Any]]:  # noqa: D401
        """Run strategy over *bars* DataFrame and return list of trade dicts.

        This method is kept for backward compatibility with the existing runner.
        """
        if bars.empty:
            return []

        bars = bars.copy().reset_index(drop=True)
        # Ensure required columns exist; fallback to Close-only bars
        if not {"high", "low"}.issubset(bars.columns):
            bars["high"] = bars["close"] * 1.0025
            bars["low"] = bars["close"] * 0.9975
        if "date" not in bars.columns:
            bars["date"] = pd.RangeIndex(len(bars))

        trades: List[TradeRecord] = []
        open_index: int | None = None
        long_short: str | None = None
        entry_price = target_price = stop_price = 0.0
        range_val = 0.0

        for i in range(1, len(bars)):
            current_bar = bars.iloc[i]

            # If in position – manage exit conditions
            if open_index is not None:
                bars_in_trade = i - open_index
                should_exit_now, exit_reason, exit_price = should_exit(
                    current_bar=current_bar,
                    direction=Direction.LONG
                    if long_short == "Long"
                    else Direction.SHORT,
                    entry_price=entry_price,
                    range_val=range_val,
                    target_rr=self.config.target_rr,
                    stop_rr=self.config.stop_rr,
                    bars_in_trade=bars_in_trade,
                    max_bars_in_trade=self.config.max_bars_in_trade,
                )

                if should_exit_now:
                    # Record trade
                    trade = TradeRecord(
                        instrument=instrument_id,
                        entry_date=str(bars.iloc[open_index]["date"]),
                        trade_type=long_short or "UNKNOWN",
                        entry_price=entry_price,
                        exit_date=str(current_bar["date"]),
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        target_price=target_price,
                        stop_price=stop_price,
                    )
                    trades.append(trade)
                    # Reset position state
                    open_index = None
                    long_short = None
                    continue

            # If flat, check for entry signal
            if open_index is None:
                direction, entry_px, range_v, _, _ = compute_signal(
                    bars, i, self.config.nr_lookback
                )

                if direction == Direction.LONG:
                    long_short = "Long"
                    entry_price = entry_px
                    range_val = range_v
                    target_price = entry_price + self.config.target_rr * range_val
                    stop_price = entry_price - self.config.stop_rr * range_val
                    open_index = i
                elif direction == Direction.SHORT:
                    long_short = "Short"
                    entry_price = entry_px
                    range_val = range_v
                    target_price = entry_price - self.config.target_rr * range_val
                    stop_price = entry_price + self.config.stop_rr * range_val
                    open_index = i

        return [t.to_dict() for t in trades]


__all__ = ["SwingRangeExpansionStrategy", "TradeRecord"]
