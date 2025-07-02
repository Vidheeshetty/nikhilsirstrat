from __future__ import annotations

from collections import deque
from typing import Deque, Optional, Tuple


class SmaFractalSignalGenerator:
    """Generates entry & stop signals based on SMA crossover + fractal breakout.

    The generator is intentionally framework-agnostic: it only consumes plain bar
    objects with .high, .low, .close attributes and returns simple tuples so that
    it can be unit-tested without NautilusTrader present.
    """

    def __init__(
        self,
        sma_short: int = 5,
        sma_long: int = 200,
        *,
        use_fractals: bool = True,
        use_sma: bool = True,
        fractal_window: int = 5,
    ):
        if sma_short >= sma_long:
            raise ValueError("Short SMA period must be < long SMA period")
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.use_fractals = use_fractals
        self.use_sma = use_sma
        self._closes: Deque[float] = deque(maxlen=sma_long)
        if fractal_window < 1 or fractal_window % 2 == 0:
            raise ValueError("fractal_window must be odd and >=1")
        self.fractal_window = fractal_window
        self._highs: Deque[float] = deque(maxlen=fractal_window)
        self._lows: Deque[float] = deque(maxlen=fractal_window)

        # Cached SMA values
        self._sma_short_val: Optional[float] = None
        self._sma_long_val: Optional[float] = None
        self._prev_trend: Optional[str] = None

    # ---------------------------------------------------------------------
    def warm_up_with_historical_data(self, historical_bars) -> None:  # noqa: D401
        """Warm up indicators with historical data before live trading starts.

        Args:
            historical_bars: List of bar objects with .high, .low, .close attributes
                            Should be in chronological order (oldest first)
        """
        if not historical_bars:
            return

        # Process historical bars to warm up indicators
        for bar in historical_bars:
            self._closes.append(float(bar.close))
            self._highs.append(float(bar.high))
            self._lows.append(float(bar.low))

            # Update SMA values as we go
            if len(self._closes) >= self.sma_short:
                self._sma_short_val = (
                    sum(list(self._closes)[-self.sma_short :]) / self.sma_short
                )
            if len(self._closes) >= self.sma_long:
                self._sma_long_val = (
                    sum(list(self._closes)[-self.sma_long :]) / self.sma_long
                )

        # Determine initial trend after warm-up (but don't set _prev_trend to avoid immediate signal)
        if (
            self.use_sma
            and self._sma_short_val is not None
            and self._sma_long_val is not None
        ):
            if self._sma_short_val > self._sma_long_val:
                self._prev_trend = "LONG"
            elif self._sma_short_val < self._sma_long_val:
                self._prev_trend = "SHORT"

        print(f"✅ Warmed up with {len(historical_bars)} historical bars")
        print(f"   SMA buffers: {len(self._closes)}/{self.sma_long} bars")
        print(f"   Fractal buffers: {len(self._highs)}/{self.fractal_window} bars")
        if self._sma_short_val and self._sma_long_val:
            print(
                f"   Current SMAs: {self._sma_short_val:.2f} / {self._sma_long_val:.2f}"
            )
            print(f"   Initial trend: {self._prev_trend}")

    def update(self, bar) -> None:  # noqa: D401
        """Update internal state with the incoming bar."""
        self._closes.append(float(bar.close))
        self._highs.append(float(bar.high))
        self._lows.append(float(bar.low))
        # Capture OI if present
        if hasattr(bar, "oi"):
            self._current_oi = getattr(bar, "oi")

        if len(self._closes) >= self.sma_short:
            self._sma_short_val = (
                sum(list(self._closes)[-self.sma_short :]) / self.sma_short
            )
        if len(self._closes) >= self.sma_long:
            self._sma_long_val = (
                sum(list(self._closes)[-self.sma_long :]) / self.sma_long
            )

    # ------------------------------------------------------------------
    def _latest_fractals(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (high_fractal, low_fractal) using the last 5 bars.

        A high fractal occurs when high[2] > high[0..4 except 2]. Same for low.
        Need a full 5-bar window.
        """
        if len(self._highs) < self.fractal_window:
            return None, None
        highs = list(self._highs)
        lows = list(self._lows)
        if self.fractal_window == 1:
            return highs[0], lows[0]
        mid = self.fractal_window // 2
        high_fractal = (
            highs[mid] if highs[mid] > max(highs[:mid] + highs[mid + 1 :]) else None
        )
        low_fractal = (
            lows[mid] if lows[mid] < min(lows[:mid] + lows[mid + 1 :]) else None
        )
        return high_fractal, low_fractal

    # ------------------------------------------------------------------
    def generate(self, bar) -> Optional[dict]:  # noqa: D401
        """Return signal dict or None.

        The logic is split so SMA and fractal filters can be toggled independently.
        """
        self.update(bar)

        # -------------------- Determine *trend* -----------------------
        trend: str | None = None
        if self.use_sma:
            # Need SMA values first
            if self._sma_short_val is None or self._sma_long_val is None:
                return None  # insufficient data
            if self._sma_short_val > self._sma_long_val:
                trend = "LONG"
            elif self._sma_short_val < self._sma_long_val:
                trend = "SHORT"
            else:
                return None

            # fire only on crossover (trend change)
            if trend == self._prev_trend:
                return None
            self._prev_trend = trend

        # -------------------- Pure fractal mode ----------------------
        high_frac, low_frac = self._latest_fractals()

        if not self.use_sma:
            # direction decided solely by breakout
            if high_frac is not None and (
                bar.high > high_frac
                or (self.fractal_window == 1 and bar.high == high_frac)
            ):
                trend = "LONG"
            elif low_frac is not None and (
                bar.low < low_frac or (self.fractal_window == 1 and bar.low == low_frac)
            ):
                trend = "SHORT"
            else:
                return None

        # If SMA used but fractals disabled, enter immediately --------
        if self.use_sma and not self.use_fractals:
            return {
                "direction": trend,
                "entry_price": bar.close,
                "stop_price": bar.low if trend == "LONG" else bar.high,
            }

        # ----------------------- SMA + fractal OR fractal-only entry ---------
        if (
            trend == "LONG"
            and high_frac is not None
            and (
                bar.high > high_frac
                or (self.fractal_window == 1 and bar.high == high_frac)
            )
        ):
            return {
                "direction": "LONG",
                "entry_price": max(bar.open, high_frac),
                "stop_price": low_frac if low_frac is not None else bar.low,
            }
        if (
            trend == "SHORT"
            and low_frac is not None
            and (
                bar.low < low_frac or (self.fractal_window == 1 and bar.low == low_frac)
            )
        ):
            return {
                "direction": "SHORT",
                "entry_price": min(bar.open, low_frac),
                "stop_price": high_frac if high_frac is not None else bar.high,
            }
        return None
