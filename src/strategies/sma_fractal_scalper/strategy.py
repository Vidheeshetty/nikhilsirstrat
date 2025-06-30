from __future__ import annotations

import logging
from typing import Any, Dict

from utils.strategy.base_strategy import BaseStrategy

from .config import SmaFractalScalperConfig
from .entry import SmaFractalSignalGenerator


class SmaFractalScalper(BaseStrategy):
    """Simple SMA + fractal breakout scalper.

    Minimal implementation: focuses on entry signal & stop placement. It does *not*
    include position sizing, trailing stops, or session cut-off yet.
    """

    config_class = SmaFractalScalperConfig

    def _setup(self) -> None:  # noqa: D401
        super()._setup()
        self.gen = SmaFractalSignalGenerator(
            self.config.sma_short_period,
            self.config.sma_long_period,
            use_fractals=self.config.use_fractals,
        )
        self.position: str | None = None  # 'LONG' / 'SHORT'
        self._entry_price: float | None = None
        self._stop_price: float | None = None
        self.trades: list[dict] = []
        self.log.setLevel(logging.INFO)

    # ------------------------------------------------------------------
    def on_bar(self, bar) -> None:  # noqa: D401
        """Handle new bar event (called by runner)."""
        signal = self.gen.generate(bar)
        # Check exit conditions first --------------------------------
        if self.position is not None:
            if self.position == "LONG" and bar.close <= (self._stop_price or 0):
                self._record_trade(bar.close, bar.timestamp)
            elif self.position == "SHORT" and bar.close >= (self._stop_price or 0):
                self._record_trade(bar.close, bar.timestamp)

        # Entry conditions -------------------------------------------
        if self.position is None and signal is not None:
            direction = signal["direction"]
            entry_px = signal["entry_price"]
            stop_px = signal["stop_price"]
            self._submit_order(direction, entry_px, stop_px, bar.timestamp)

    # ------------------------------------------------------------------
    # Helpers – these simply log right now; wire to NautilusTrader later
    # ------------------------------------------------------------------
    def _submit_order(self, direction: str, price: float, stop: float, ts: Any) -> None:
        order = {
            "direction": direction,
            "qty": 1,  # TODO: use risk_per_trade sizing
            "price": price,
            "stop_px": stop,
            "timestamp": ts,
        }
        self.position = direction
        self._entry_price = price
        self._stop_price = stop
        self.log.info("New %s order @ %.2f (SL %.2f)", direction, price, stop)
        # In live version: send to broker via trade engine

    # ------------------------------------------------------------------
    def on_stop(self) -> None:  # noqa: D401
        self.log.info("Strategy stopped. Closing position if any.")
        self.position = None

    def on_quote(self, price: float):  # noqa: D401
        """Handle raw price quote (float) – mainly for stub-engine backtests.

        We create a synthetic OHLC bar where open=close=price and high/low are
        +-0.25%% around *price*.  This mirrors other stub strategies so the
        shared EngineManager + BacktestEngine wrapper can feed floats yet the
        SMA/fractal logic still receives bar objects.
        """
        class _Bar:  # lightweight anonymous struct
            __slots__ = ("open", "high", "low", "close", "timestamp")

            def __init__(self, p, idx):
                self.open = p
                self.close = p
                self.high = p * 1.0025
                self.low = p * 0.9975
                self.timestamp = idx

        idx = getattr(self, "_tick_index", 0)
        bar = _Bar(price, idx)
        self._tick_index = idx + 1
        self.on_bar(bar)

    # ------------------------------------------------------------------
    def _record_trade(self, exit_price: float, ts: Any) -> None:
        if self._entry_price is None or self.position is None:
            return
        realised = (
            exit_price - self._entry_price
            if self.position == "LONG"
            else self._entry_price - exit_price
        )
        pct = (realised / self._entry_price * 100) if self._entry_price else 0.0
        self.trades.append(
            {
                "Instrument": "UNKNOWN",  # filled by runner
                "Entry_Date": "N/A",
                "Trade_Type": "Long" if self.position == "LONG" else "Short",
                "Exit_Reason": "SL_HIT",
                "Entry_Price": round(self._entry_price, 2),
                "IV": None,
                "OI": None,
                "Exit_Date": "N/A",
                "Exit_Price": round(exit_price, 2),
                "Threshold": None,
                "SL_Price": round(self._stop_price or 0.0, 2),
                "Realised_PnL": round(realised, 2),
                "PnL%": round(pct, 2),
                "MDD_pct": None,
                "Sharpe": None,
                "Cum_PnL": None,
            }
        )
        # reset position
        self.position = None
        self._entry_price = None
        self._stop_price = None
        # Allow new entries in same trend after exit
        try:
            self.gen._prev_trend = None  # type: ignore[attr-defined,protected-access]
        except Exception:
            pass 