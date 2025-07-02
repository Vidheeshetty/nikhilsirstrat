from __future__ import annotations

import logging
from typing import Any, Dict
from datetime import datetime

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
            use_sma=self.config.use_sma,
            fractal_window=self.config.fractal_window,
        )
        self.position: str | None = None  # 'LONG' / 'SHORT'
        self._entry_price: float | None = None
        self._stop_price: float | None = None
        self.trades: list[dict] = []
        self.log.setLevel(logging.DEBUG if logging.getLogger().level == logging.DEBUG else logging.INFO)

    # ------------------------------------------------------------------
    def on_bar(self, bar) -> None:  # noqa: D401
        """Handle new bar event (called by runner)."""
        signal = self.gen.generate(bar)
        self.log.debug(
            "Bar received: O=%.2f H=%.2f L=%.2f C=%.2f, signal=%s",
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            signal,
        )
        # Extract timestamp in flexible manner
        ts_val = getattr(bar, "timestamp", getattr(bar, "ts_event", getattr(bar, "ts_init", None)))
        # Update last seen price for graceful exit
        self._last_price = bar.close

        # ------------------------------------------------------------------
        # Extra diagnostics when NO signal is generated.
        # ------------------------------------------------------------------

        if signal is None:
            reason_parts: list[str] = []

            # 1) SMA warm-up check ------------------------------------------------
            closes_len = len(self.gen._closes)  # type: ignore[attr-defined]
            if self.gen.use_sma and closes_len < self.gen.sma_long:  # type: ignore[attr-defined]
                reason_parts.append(
                    f"SMA warm-up: {closes_len}/{self.gen.sma_long} bars collected"
                )

            # 1b) SMA trend unchanged (crossover already happened earlier) ------
            if (
                self.gen.use_sma
                and self.gen._sma_short_val is not None
                and self.gen._sma_long_val is not None
                and self.gen._prev_trend is not None
            ):  # type: ignore[attr-defined]
                # compute live trend again for clarity
                latest_trend = "LONG" if self.gen._sma_short_val > self.gen._sma_long_val else "SHORT"  # type: ignore[attr-defined]
                if latest_trend == self.gen._prev_trend:  # type: ignore[attr-defined]
                    reason_parts.append(
                        f"Trend unchanged ({latest_trend}); waiting for opposite crossover"
                    )

            # 2) Determine current trend (if SMA ready) ------------------------
            current_trend: str | None = None
            if self.gen.use_sma and self.gen._sma_short_val is not None and self.gen._sma_long_val is not None:  # type: ignore[attr-defined]
                if self.gen._sma_short_val > self.gen._sma_long_val:  # type: ignore[attr-defined]
                    current_trend = "LONG"
                elif self.gen._sma_short_val < self.gen._sma_long_val:  # type: ignore[attr-defined]
                    current_trend = "SHORT"

            # If SMA is disabled, the trend will be decided solely by fractal
            if not self.gen.use_sma:
                current_trend = None  # unknown until breakout

            # 3) Fractal breakout gap -----------------------------------------
            high_frac, low_frac = self.gen._latest_fractals()  # type: ignore[attr-defined]

            # Fractal warm-up
            if (
                self.gen.use_fractals
                and len(self.gen._highs) < self.gen.fractal_window  # type: ignore[attr-defined]
            ):
                reason_parts.append(
                    f"Fractal warm-up: {len(self.gen._highs)}/{self.gen.fractal_window} bars collected"
                )

            gap_msg = None
            if current_trend == "LONG" and high_frac is not None:
                gap_val = round(high_frac - bar.high, 5)
                if gap_val > 0:
                    gap_msg = (
                        f"LONG gap: need +{gap_val:.2f} (bar.high={bar.high:.2f} vs fractal={high_frac:.2f})"
                    )
                elif gap_val == 0:
                    gap_msg = (
                        "LONG gap: price has reached fractal level "
                        f"({bar.high:.2f}) but must exceed it to trigger"
                    )
            elif current_trend == "SHORT" and low_frac is not None:
                gap_val = round(bar.low - low_frac, 5)
                if gap_val > 0:
                    gap_msg = (
                        f"SHORT gap: need -{gap_val:.2f} (bar.low={bar.low:.2f} vs fractal={low_frac:.2f})"
                    )
                elif gap_val == 0:
                    gap_msg = (
                        "SHORT gap: price has reached fractal level "
                        f"({bar.low:.2f}) but must break below to trigger"
                    )

            if gap_msg:
                reason_parts.append(gap_msg)

            # If SMA disabled and fractals ready but price hasn't broken out ----
            if (
                not self.gen.use_sma
                and high_frac is not None
                and low_frac is not None
                and gap_msg is None
            ):
                reason_parts.append("Price has not broken fractal level yet")

            if not reason_parts:
                # Fallback generic note so caller knows diagnostic ran
                reason_parts.append("Conditions not met for entry")

            self.log.debug("No signal reason(s): %s", " | ".join(reason_parts))

        # Check exit conditions first --------------------------------
        if self.position is not None:
            # 1) Stop-loss hit
            if self.position == "LONG" and bar.close <= (self._stop_price or 0):
                self._record_trade(bar.close, ts_val, reason="SL_HIT")
            elif self.position == "SHORT" and bar.close >= (self._stop_price or 0):
                self._record_trade(bar.close, ts_val, reason="SL_HIT")

            # 2) Trend reversal – opposite SMA crossover
            elif signal is not None and signal["direction"] != self.position:
                self._record_trade(bar.close, ts_val, reason="REVERSAL")
                # After closing, enter new trade per fresh signal
                direction = signal["direction"]
                oi_val = getattr(self.gen, "_current_oi", None)
                self._submit_order(direction, bar.close, bar.low if direction=="LONG" else bar.high, ts_val, oi_val)
                return

        # Entry conditions -------------------------------------------
        if self.position is None and signal is not None:
            self.log.info("Signal: direction=%s entry=%.2f stop=%.2f", signal["direction"], signal["entry_price"], signal["stop_price"])  # noqa: E501
            direction = signal["direction"]
            entry_px = signal["entry_price"]
            stop_px = signal["stop_price"]
            oi_val = getattr(self.gen, "_current_oi", None)
            self._submit_order(direction, entry_px, stop_px, ts_val, oi_val)

    # ------------------------------------------------------------------
    # Helpers – these simply log right now; wire to NautilusTrader later
    # ------------------------------------------------------------------
    def _submit_order(
        self,
        direction: str,
        price: float,
        stop: float,
        ts: Any,
        oi: float | None = None,
    ) -> None:
        # Record entry timestamp (nanoseconds if available, else idx)
        self._entry_ts = ts

        price = float(price)
        stop = float(stop)
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
        self._entry_oi = oi
        self.log.info("New %s order @ %.2f (SL %.2f)", direction, price, stop)
        # In live version: send to broker via trade engine

    # ------------------------------------------------------------------
    def on_stop(self) -> None:  # noqa: D401
        self.log.info("Strategy stopped. Closing position if any.")
        if self.position is not None and self._entry_price is not None:
            price = getattr(self, "_last_price", self._entry_price)
            self._record_trade(price, ts="END", reason="END")
        self.position = None

    def on_quote(self, price: float):  # noqa: D401
        self.log.debug("Raw quote received: %.2f", price)
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
                self.high = p * 1.0025  # +0.25% envelope
                self.low = p * 0.9975   # -0.25% envelope
                self.timestamp = idx

        idx = getattr(self, "_tick_index", 0)
        bar = _Bar(price, idx)
        self._tick_index = idx + 1
        self.on_bar(bar)

    # ------------------------------------------------------------------
    def _record_trade(self, exit_price: float, ts: Any, reason: str) -> None:
        if self._entry_price is None or self.position is None:
            return
        from datetime import datetime

        def _ts_to_date(val: Any) -> str:
            try:
                ns = int(val)
                if ns > 1_000_000_000_000:  # nanoseconds timestamp
                    return datetime.utcfromtimestamp(ns / 1_000_000_000).strftime("%Y-%m-%d")
                # else treat as counter -> use current date
            except Exception:
                pass
            return datetime.utcnow().strftime("%Y-%m-%d")

        exit_price = float(exit_price)
        realised = (
            exit_price - self._entry_price
            if self.position == "LONG"
            else self._entry_price - exit_price
        )
        pct = (realised / self._entry_price * 100) if self._entry_price else 0.0
        self.trades.append(
            {
                "Instrument": "UNKNOWN",  # filled by runner
                "Entry_Date": _ts_to_date(self._entry_ts),
                "Trade_Type": "Long" if self.position == "LONG" else "Short",
                "Exit_Reason": reason,
                "Entry_Price": round(self._entry_price, 2),
                "IV": None,
                "OI": getattr(self, "_entry_oi", None),
                "Exit_Date": _ts_to_date(ts) if ts != "END" else _ts_to_date(self._entry_ts),
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