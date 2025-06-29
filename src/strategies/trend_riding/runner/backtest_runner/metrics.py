from __future__ import annotations

from typing import List

"""Performance metrics helper (placeholder)."""


def calculate_pnl(prices: List[float], entry_price: float, exit_price: float) -> float:  # noqa: D401,E501
    """Return simple PnL based on entry/exit prices."""
    return exit_price - entry_price


__all__ = ["calculate_pnl"]
