from __future__ import annotations

"""Entry signal logic for Trend-Riding strategy.

**Current behaviour** (placeholder):
Entry whenever the *n*-period close is above the *n*-period simple moving
average by more than *threshold_pct*.

This is intentionally simplistic so that unit tests can exercise the module
without needing extensive historical data. Replace with actual logic later.
"""

from typing import Sequence

from utils.strategy.indicators import sma


def should_enter(prices: Sequence[float], period: int = 15, threshold_pct: float = 0.0) -> bool:  # noqa: D401
    """Decide whether to open a long position.

    For now we only consider long entries: *close* > SMA(period) * (1 + threshold_pct).
    """
    avg = sma(prices, period)
    return prices[-1] > avg * (1 + threshold_pct)


__all__ = ["should_enter"]
