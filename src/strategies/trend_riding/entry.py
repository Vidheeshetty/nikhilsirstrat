from __future__ import annotations

from typing import Sequence

from .breakout import previous_top_bottom, breakout_signal, Direction

"""Entry signal computation for Trend-Riding strategy.

The primary function `compute_signal()` combines Dow-theory breakouts
with position-aware logic. This module is stateless and can be
unit-tested independently of the main Strategy class.

The implementation handles both LONG and SHORT breakouts with configurable
buffer percentages to avoid false signals.
"""


def compute_signal(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    period: int,
    buffer_pct: float,
) -> Direction:  # noqa: D401
    """Return breakout **Direction** (LONG / SHORT / NONE).

    Raises ``ValueError`` if not enough data.
    """

    if len(closes) < period + 1:
        raise ValueError("Not enough data for breakout calculation")

    prev_top, prev_bottom = previous_top_bottom(highs[:-1], lows[:-1], period)
    return breakout_signal(closes[-1], prev_top, prev_bottom, buffer_pct)


__all__ = ["compute_signal", "Direction"]


# ------------------------------------------------------------------
# Backwards-compat helper – returns bool for LONG breakout only
# ------------------------------------------------------------------


def should_enter(
    prices: Sequence[float], *, period: int = 15, buffer_pct: float = 2.0
) -> bool:  # noqa: D401
    """Legacy wrapper kept for existing unit tests.

    Treats *prices* as closes and returns *True* for LONG breakout.
    """
    try:
        sig = compute_signal(
            prices, prices, prices, period=period, buffer_pct=buffer_pct
        )  # type: ignore[arg-type]
    except ValueError:
        raise  # Propagate
    return sig == Direction.LONG


__all__.append("should_enter")
