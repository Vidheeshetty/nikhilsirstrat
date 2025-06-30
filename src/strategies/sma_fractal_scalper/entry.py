from __future__ import annotations

import collections
from collections import deque
from typing import Deque, Optional, Tuple


class SmaFractalSignalGenerator:
    """Generates entry & stop signals based on SMA crossover + fractal breakout.

    The generator is intentionally framework-agnostic: it only consumes plain bar
    objects with .high, .low, .close attributes and returns simple tuples so that
    it can be unit-tested without NautilusTrader present.
    """

    def __init__(self, sma_short: int = 5, sma_long: int = 200, *, use_fractals: bool = True):
        if sma_short >= sma_long:
            raise ValueError("Short SMA period must be < long SMA period")
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.use_fractals = use_fractals
        self._closes: Deque[float] = deque(maxlen=sma_long)
        # We keep last 5 highs/lows to detect fractals (bar[2] is center)
        self._highs: Deque[float] = deque(maxlen=5)
        self._lows: Deque[float] = deque(maxlen=5)

        # Cached SMA values
        self._sma_short_val: Optional[float] = None
        self._sma_long_val: Optional[float] = None
        self._prev_trend: Optional[str] = None

    # ---------------------------------------------------------------------
    def update(self, bar) -> None:  # noqa: D401
        """Update internal state with the incoming bar."""
        self._closes.append(bar.close)
        self._highs.append(bar.high)
        self._lows.append(bar.low)

        if len(self._closes) >= self.sma_short:
            self._sma_short_val = sum(list(self._closes)[-self.sma_short:]) / self.sma_short
        if len(self._closes) == self.sma_long:
            self._sma_long_val = sum(self._closes) / self.sma_long

    # ------------------------------------------------------------------
    def _latest_fractals(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (high_fractal, low_fractal) using the last 5 bars.

        A high fractal occurs when high[2] > high[0..4 except 2]. Same for low.
        Need a full 5-bar window.
        """
        if len(self._highs) < 5:
            return None, None
        highs = list(self._highs)
        lows = list(self._lows)
        high_fractal = highs[2] if highs[2] > max(highs[0], highs[1], highs[3], highs[4]) else None
        low_fractal = lows[2] if lows[2] < min(lows[0], lows[1], lows[3], lows[4]) else None
        return high_fractal, low_fractal

    # ------------------------------------------------------------------
    def generate(self, bar) -> Optional[dict]:  # noqa: D401
        """Return signal dict or None.

        dict keys: direction ('LONG'/'SHORT'), entry_price, stop_price
        """
        self.update(bar)
        if self._sma_short_val is None or self._sma_long_val is None:
            return None  # not enough data yet

        trend = None
        if self._sma_short_val > self._sma_long_val:
            trend = "LONG"
        elif self._sma_short_val < self._sma_long_val:
            trend = "SHORT"
        else:
            return None

        # trigger only on trend change between bars
        if trend == self._prev_trend:
            return None

        self._prev_trend = trend

        # If fractal filter disabled, enter immediately on crossover
        if not self.use_fractals:
            return {
                "direction": trend,
                "entry_price": bar.close,
                "stop_price": bar.low if trend == "LONG" else bar.high,
            }

        high_frac, low_frac = self._latest_fractals()
        if trend == "LONG" and high_frac is not None and bar.close > high_frac:
            return {
                "direction": "LONG",
                "entry_price": bar.close,
                "stop_price": low_frac if low_frac else bar.low,  # fall-back
            }
        if trend == "SHORT" and low_frac is not None and bar.close < low_frac:
            return {
                "direction": "SHORT",
                "entry_price": bar.close,
                "stop_price": high_frac if high_frac else bar.high,
            }
        return None 