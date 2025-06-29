"""Breakout detection helpers for Trend-Riding.

Implements the Dow-theory breakout rules described in the strategy doc.

Functions are decoupled from Strategy so we can unit-test them easily.
"""

from enum import Enum, auto
from typing import Sequence, Tuple


class Direction(Enum):
    NONE = auto()
    LONG = auto()
    SHORT = auto()


# ---------------------------------------------------------------------


def previous_top_bottom(
    highs: Sequence[float], lows: Sequence[float], lookback: int
) -> Tuple[float, float]:  # noqa: D401
    """Return (prev_top, prev_bottom) over *lookback* bars.

    Caller must ensure *lookback* elements exist.
    """
    slice_high = highs[-lookback:]
    slice_low = lows[-lookback:]
    return max(slice_high), min(slice_low)


def breakout_signal(
    close: float,
    prev_top: float,
    prev_bottom: float,
    buffer_pct: float,
) -> Direction:  # noqa: D401
    """Return LONG / SHORT / NONE breakout signal.

    *buffer_pct* is applied symmetrically around the levels.
    """
    if close > prev_top * (1 + buffer_pct / 100):
        return Direction.LONG
    if close < prev_bottom * (1 - buffer_pct / 100):
        return Direction.SHORT
    return Direction.NONE


__all__ = ["Direction", "previous_top_bottom", "breakout_signal"]
