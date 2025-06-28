from __future__ import annotations

"""Exit logic for Trend-Riding strategy – placeholder implementation."""

from typing import Sequence


def should_exit(prices: Sequence[float], entry_price: float, sl_pct: float, tp_pct: float) -> bool:  # noqa: D401,E501
    """Return *True* if stop-loss or take-profit level is hit.

    This helper can be used by the Strategy or a RiskManager layer.
    """
    if not prices:
        raise ValueError("prices cannot be empty")
    last_price = prices[-1]
    if last_price <= entry_price * (1 - sl_pct):
        return True  # stop-loss hit
    if last_price >= entry_price * (1 + tp_pct):
        return True  # take-profit reached
    return False


__all__ = ["should_exit"]
