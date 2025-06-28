from __future__ import annotations

"""Common indicator helpers (zero external dependencies).

Contains lightweight SMA & EMA implementations so core strategy code can rely
on centralised, tested utilities.
"""

from typing import Sequence


def sma(series: Sequence[float], period: int) -> float:  # noqa: D401
    if period <= 0:
        raise ValueError("period must be > 0")
    if len(series) < period:
        raise ValueError("insufficient data for SMA")
    return sum(series[-period:]) / period


def ema(series: Sequence[float], period: int) -> float:  # noqa: D401
    if period <= 0:
        raise ValueError("period must be > 0")
    if len(series) < period:
        raise ValueError("insufficient data for EMA")
    k = 2 / (period + 1)
    ema_val = sma(series[:period], period)
    for price in series[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


__all__ = ["sma", "ema"]
