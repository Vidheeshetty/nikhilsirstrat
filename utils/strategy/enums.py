from __future__ import annotations

from enum import Enum, auto

"""Common enums used across trading strategies."""


class Direction(Enum):
    """Trade direction enum."""

    NONE = "NONE"
    LONG = "LONG"
    SHORT = "SHORT"


class ExitReason(Enum):
    """Exit reason constants."""

    STOP_LOSS = "SL"
    TAKE_PROFIT = "TP"
    TIME_LIMIT = "TIME"
    REVERSAL = "REV"  # For SAR-style reversals
    NONE = "NONE"


class OrderSide(Enum):
    """Order side enum."""

    BUY = auto()
    SELL = auto()


__all__ = ["Direction", "ExitReason", "OrderSide"]
