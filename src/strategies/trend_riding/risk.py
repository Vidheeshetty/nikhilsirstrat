from __future__ import annotations

from typing import Sequence

from .exit import should_exit
from .entry import Direction

"""High-level risk management helpers for Trend-Riding strategy."""


class RiskManager:  # pylint: disable=too-few-public-methods
    """Evaluate exit conditions based on price series and config params."""

    def __init__(self, sl_pct: float, tp_pct: float):
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct

    def hit(
        self,
        prices: Sequence[float],
        entry_price: float,
        side: Direction = Direction.LONG,
    ) -> bool:
        """Return *True* if SL/TP triggered."""
        return should_exit(prices, entry_price, self.sl_pct, self.tp_pct, side=side)


__all__ = ["RiskManager"]
