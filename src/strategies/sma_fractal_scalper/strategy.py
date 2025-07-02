from __future__ import annotations

import logging
from typing import Any
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

    def __init__(
        self, config: SmaFractalScalperConfig, broker_manager=None, instrument_id=None
    ):
        """Initialize the SMA Fractal Scalper strategy."""
        # Store additional parameters before calling super()
        self._broker_manager = broker_manager
        self._init_instrument_id = instrument_id
        super().__init__(config)

    def _setup(self) -> None:  # noqa: D401
        """Setup the strategy after base initialization."""
        super()._setup()

        self.gen = SmaFractalSignalGenerator(
            sma_short=self.config.sma_short_period,
            sma_long=self.config.sma_long_period,
            use_fractals=self.config.use_fractals,
            use_sma=self.config.use_sma,
            fractal_window=self.config.fractal_window,
        )

        # Trading state
        self.position: str | None = None  # "LONG", "SHORT", or None
        self.trades: list[dict] = []  # Store completed trades
        self._entry_price: float | None = None
        self._stop_price: float | None = None
        self._entry_ts: Any = None
        self._entry_oi: float | None = None
        self._last_price: float | None = None
        self._instrument_id: str | None = self._init_instrument_id

        # Broker integration
        self.broker_manager = self._broker_manager
        self._pending_orders: dict[str, Any] = {}  # Track pending orders

        # Historical warm-up will be triggered when instrument ID is set
        self._warmup_pending = self.config.historical_warmup
        self.log.setLevel(
            logging.DEBUG
            if logging.getLogger().level == logging.DEBUG
            else logging.INFO
        )

    def set_instrument_id(self, instrument_id: str) -> None:  # noqa: D401
        """Set the instrument ID for this strategy instance."""
        self._instrument_id = instrument_id

        # Trigger historical warm-up now that instrument ID is available
        if getattr(self, "_warmup_pending", False):
            self._warm_up_indicators()
            self._warmup_pending = False

    def _warm_up_indicators(self) -> None:  # noqa: D401
        """Load historical data to warm up SMA and fractal indicators."""
        try:
            from .historical_loader import HistoricalDataLoader

            # Get instrument ID from the runner context if available
            instrument_id = getattr(self, "_instrument_id", None)
            if not instrument_id:
                self.log.warning("No instrument ID available for historical warm-up")
                return

            # Initialize historical data loader
            loader = HistoricalDataLoader()

            # Load historical bars for warm-up
            historical_bars = loader.get_warm_up_bars(
                instrument_id=instrument_id,
                sma_long_period=self.config.sma_long_period,
                fractal_window=self.config.fractal_window,
                strategy="recent",  # or "previous_day"
            )

            if historical_bars:
                self.log.info(
                    f"🔥 Warming up indicators with {len(historical_bars)} historical bars"
                )
                self.gen.warm_up_with_historical_data(historical_bars)
                self.log.info("✅ Strategy ready to trade immediately!")
            else:
                self.log.warning(
                    "No historical data available - strategy will warm up with live data"
                )

        except Exception as e:
            self.log.error(f"Failed to warm up indicators: {e}")
            self.log.info("Strategy will start without historical warm-up")

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
        ts_val = getattr(
            bar, "timestamp", getattr(bar, "ts_event", getattr(bar, "ts_init", None))
        )
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
                latest_trend = (
                    "LONG"
                    if self.gen._sma_short_val > self.gen._sma_long_val
                    else "SHORT"
                )  # type: ignore[attr-defined]
                if latest_trend == self.gen._prev_trend:  # type: ignore[attr-defined]
                    reason_parts.append(
                        f"Trend unchanged ({latest_trend}); waiting for opposite crossover"
                    )

            # 2) Determine current trend (if SMA ready) ------------------------
            current_trend: str | None = None
            if (
                self.gen.use_sma
                and self.gen._sma_short_val is not None
                and self.gen._sma_long_val is not None
            ):  # type: ignore[attr-defined]
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
                self.gen.use_fractals and len(self.gen._highs) < self.gen.fractal_window  # type: ignore[attr-defined]
            ):
                reason_parts.append(
                    f"Fractal warm-up: {len(self.gen._highs)}/{self.gen.fractal_window} bars collected"
                )

            gap_msg = None
            if current_trend == "LONG" and high_frac is not None:
                gap_val = round(high_frac - bar.high, 5)
                if gap_val > 0.00001:  # Use epsilon for floating point comparison
                    gap_msg = f"LONG gap: need {gap_val:.2f} higher (bar.high={bar.high:.2f} vs fractal={high_frac:.2f})"
                else:  # gap_val <= 0.00001 (essentially zero or negative)
                    gap_msg = (
                        "LONG gap: price has reached fractal level "
                        f"({bar.high:.2f}) but must exceed it to trigger"
                    )
            elif current_trend == "SHORT" and low_frac is not None:
                gap_val = round(low_frac - bar.low, 5)
                if gap_val > 0.00001:  # Use epsilon for floating point comparison
                    gap_msg = f"SHORT gap: need {gap_val:.2f} lower (bar.low={bar.low:.2f} vs fractal={low_frac:.2f})"
                else:  # gap_val <= 0.00001 (essentially zero or negative)
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
                self._submit_order(
                    direction,
                    bar.close,
                    bar.low if direction == "LONG" else bar.high,
                    ts_val,
                    oi_val,
                )
                return

        # Entry conditions -------------------------------------------
        if self.position is None and signal is not None:
            self.log.info(
                "Signal: direction=%s entry=%.2f stop=%.2f",
                signal["direction"],
                signal["entry_price"],
                signal["stop_price"],
            )  # noqa: E501
            direction = signal["direction"]
            entry_px = signal["entry_price"]
            stop_px = signal["stop_price"]
            oi_val = getattr(self.gen, "_current_oi", None)
            self._submit_order(direction, entry_px, stop_px, ts_val, oi_val)

    # ------------------------------------------------------------------
    # Helpers – these will submit actual orders to the broker
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

        # Update internal state
        self.position = direction
        self._entry_price = price
        self._stop_price = stop
        self._entry_oi = oi

        # If no broker manager, just log (backward compatibility)
        if self.broker_manager is None:
            self.log.info(
                "New %s order @ %.2f (SL %.2f) - NO BROKER INTEGRATION",
                direction,
                price,
                stop,
            )
            return

        # Prepare order data for async submission by runner
        try:
            import uuid

            # Generate unique order ID
            order_id = f"SMA_SCALP_{uuid.uuid4().hex[:8].upper()}"

            # Store pending order for runner to process
            order_data = {
                "order_id": order_id,
                "direction": direction,
                "entry_price": price,
                "stop_price": stop,
                "instrument_id": self._instrument_id or "UNKNOWN",
                "quantity": 1,  # TODO: implement proper position sizing
                "timestamp": ts,
                "submitted": False,
            }

            self._pending_orders[order_id] = order_data

            self.log.info(
                "✅ Prepared %s order @ %.2f (SL %.2f) - Order ID: %s",
                direction,
                price,
                stop,
                order_id,
            )

        except Exception as e:
            self.log.error("❌ Failed to prepare order: %s", e)
            self.log.info(
                "📝 Logged %s order @ %.2f (SL %.2f) - Order preparation failed",
                direction,
                price,
                stop,
            )

    def get_pending_orders(self) -> dict[str, Any]:
        """Get pending orders that need to be submitted by the runner."""
        return {
            k: v
            for k, v in self._pending_orders.items()
            if not v.get("submitted", False)
        }

    def mark_order_submitted(self, order_id: str, broker_order_id: str = None) -> None:
        """Mark an order as submitted to the broker."""
        if order_id in self._pending_orders:
            self._pending_orders[order_id]["submitted"] = True
            self._pending_orders[order_id]["broker_order_id"] = broker_order_id
            self.log.info(
                "📤 Order %s submitted to broker: %s", order_id, broker_order_id
            )

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
                self.low = p * 0.9975  # -0.25% envelope
                self.timestamp = idx

        idx = getattr(self, "_tick_index", 0)
        bar = _Bar(price, idx)
        self._tick_index = idx + 1
        self.on_bar(bar)

    # ------------------------------------------------------------------
    def _record_trade(self, exit_price: float, ts: Any, reason: str) -> None:
        if self._entry_price is None or self.position is None:
            return

        def _ts_to_date(val: Any) -> str:
            try:
                ns = int(val)
                if ns > 1_000_000_000_000:  # nanoseconds timestamp
                    return datetime.utcfromtimestamp(ns / 1_000_000_000).strftime(
                        "%Y-%m-%d"
                    )
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
                "Exit_Date": _ts_to_date(ts)
                if ts != "END"
                else _ts_to_date(self._entry_ts),
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
