from __future__ import annotations

from typing import List, Callable, Any

"""Lightweight stub BacktestEngine to decouple unit tests from Nautilus-Trader."""


class BacktestEngine:  # pylint: disable=too-few-public-methods
    """A VERY small wrapper around a strategy callable for fast unit tests.

    This is *NOT* a production-grade engine – just enough to execute the
    strategy against a list of prices or bar objects. Integration tests can later
    switch to the real Nautilus engine behind the same interface.

    Parameters
    ----------
    callback : Callable[[Any], Any], optional
        Generic callback to invoke for each data element.
    on_quote : Callable[[Any], Any], optional
        Alias for *callback* kept for backward-compatibility with legacy unit tests
        that expect an ``on_quote`` parameter.
    on_bar : Callable[[Any], Any], optional
        Alternative alias accepted in some test-suites.
    """

    def __init__(self, callback: Callable[[Any], Any] | None = None, **kwargs):
        # Backwards compatibility: allow passing ``on_quote`` or ``on_bar`` keyword args
        if callback is None:
            callback = kwargs.get("on_quote") or kwargs.get("on_bar")

        if callback is None:
            raise ValueError(
                "BacktestEngine requires a callback, got None. Provide 'callback', 'on_quote', or 'on_bar'."
            )

        self._callback = callback

    def run(self, data: List[Any]):
        """Run the backtest by calling the callback for each data item.

        The callback could be on_quote (expecting float) or on_bar (expecting bar object).
        We simply pass each data item to the callback as-is.
        """
        for item in data:
            self._callback(item)


__all__ = ["BacktestEngine"]
