from __future__ import annotations

"""TrendRidingStrategy – minimal implementation compatible with new scaffold."""

from typing import Sequence, List
from utils.strategy.base_strategy import BaseStrategy
from .config import TrendRidingConfig
from .entry import should_enter
from .risk import RiskManager
from .position import calculate_size


class TrendRidingStrategy(BaseStrategy):
    """A placeholder strategy that counts quotes and uses helpers.

    The real trading logic will be fleshed out in subsequent iterations.
    """

    config_class = TrendRidingConfig

    def _setup(self) -> None:  # noqa: D401,override
        self._prices: List[float] = []
        self._in_position: bool = False
        self._entry_price: float | None = None
        self.risk_mgr = RiskManager(self.config.sl_pct, self.config.tp_pct)
        super()._setup()

    # ------------------------------------------------------------------
    # Mocked hooks – in real environment quotes/bars carry rich info objects
    # ------------------------------------------------------------------
    def on_quote(self, price: float):  # noqa: D401,override – simplified
        """Process a new quote price (float for unit-test simplicity)."""
        self._prices.append(price)

        if not self._in_position:
            try:
                if should_enter(self._prices, period=self.config.lookback_intervals):
                    self._enter_trade(price)
            except ValueError:
                # Not enough data yet – nothing to do
                pass
        elif self._in_position and self.risk_mgr.hit(self._prices, self._entry_price):  # type: ignore[arg-type]
            self._exit_trade(price)

    # ------------------------------------------------------------------
    def _enter_trade(self, price: float) -> None:
        size = calculate_size(capital=100_000, risk_per_trade_pct=0.01, price=price, sl_pct=self.config.sl_pct)
        self.log.info("Entering position at %.2f, size=%s", price, size)
        self._in_position = True
        self._entry_price = price

    def _exit_trade(self, price: float) -> None:
        pnl = price - (self._entry_price or 0.0)
        self.log.info("Exiting position at %.2f, PnL=%.2f", price, pnl)
        self._in_position = False
        self._entry_price = None

    # ------------------------------------------------------------------
    def on_stop(self):  # noqa: D401,override
        super().on_stop()
        self.log.info("Processed %s quotes in total.", len(self._prices))


__all__ = ["TrendRidingStrategy"]
