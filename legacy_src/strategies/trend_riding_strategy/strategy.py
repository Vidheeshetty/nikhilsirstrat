"""TrendRidingStrategy – minimal stub.

A placeholder implementation which simply logs quote ticks. The real
algorithm will be ported in a later round.
"""

from __future__ import annotations

from nautilus_trader.trading.strategy import Strategy  # type: ignore
from typing import Any


class TrendRidingStrategy(Strategy):
    """A placeholder strategy that does nothing but accept ticks."""

    config_class: Any = object  # replace with real config dataclass later

    def __init__(self, config):  # noqa: D401
        super().__init__(config=config)
        self._count = 0

    # NautilusTrader hook ------------------------------------------------
    def on_quote(self, quote):  # noqa: D401
        # Increment internal counter; used as a sanity check during testing.
        self._count += 1
        if self._count % 10_000 == 0:
            self.log.info(f"Received {self._count} quotes so far.")

    def on_stop(self):  # noqa: D401
        self.log.info("TrendRidingStrategy stopped. Processed %s quotes.", self._count) 