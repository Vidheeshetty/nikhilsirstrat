from __future__ import annotations

"""Lightweight stub BacktestEngine to decouple unit tests from Nautilus-Trader."""

from typing import List, Callable, Any


class BacktestEngine:  # pylint: disable=too-few-public-methods
    """A VERY small wrapper around a strategy callable for fast unit tests.

    This is *NOT* a production-grade engine – just enough to execute the
    TrendRidingStrategy against a list of prices. Integration tests can later
    switch to the real Nautilus engine behind the same interface.
    """

    def __init__(self, on_quote: Callable[[float], Any]):
        self._on_quote = on_quote

    def run(self, prices: List[float]):
        for p in prices:
            self._on_quote(p)


__all__ = ["BacktestEngine"]
