from __future__ import annotations

from typing import List, Optional

from utils.strategy.base_strategy import BaseStrategy
from .config import TrendRidingConfig
from .entry import compute_signal, Direction
from .risk import RiskManager
from .position import calculate_size

"""TrendRidingStrategy – minimal implementation compatible with new scaffold."""


class TrendRidingStrategy(BaseStrategy):
    """A placeholder strategy that counts quotes and uses helpers.

    The real trading logic will be fleshed out in subsequent iterations.
    """

    config_class = TrendRidingConfig

    def _setup(self) -> None:  # noqa: D401,override
        self._prices: List[float] = []
        self._in_position: bool = False
        self._entry_price: Optional[float] = None
        self._position_side: Optional[Direction] = None  # None until entry
        self.risk_mgr = RiskManager(self.config.sl_pct, self.config.tp_pct)
        super()._setup()

    # ------------------------------------------------------------------
    # Mocked hooks – in real environment quotes/bars carry rich info objects
    # ------------------------------------------------------------------
    def on_quote(self, price: float):  # noqa: D401,override – simplified
        """Process a new quote price (float for unit-test simplicity).

        Our stub feed only provides *close*; we imitate OHLC by setting high =
        low = close so the breakout logic still works with real bars.
        """

        # We store prices in three parallel lists for compatibility with real
        # OHLC inputs (allows seamless upgrade once DataManager returns bars).
        self._prices.append(price)

        # --------------------------------------------------------------
        # ENTRY – check breakout vs previous top/bottom
        # --------------------------------------------------------------
        if not self._in_position:
            try:
                sig = compute_signal(
                    highs=self._prices,
                    lows=self._prices,
                    closes=self._prices,
                    period=self.config.lookback_intervals,
                    buffer_pct=self.config.entry_buffer_pct,
                )
            except ValueError:
                return  # not enough bars yet

            if sig in (Direction.LONG, Direction.SHORT):
                self._enter_trade(price, sig)
        else:
            # -----------------------------------------------------------
            # EXIT – risk manager or opposite breakout (SAR if enabled)
            # -----------------------------------------------------------
            if self.risk_mgr.hit(
                self._prices,
                self._entry_price,
                side=self._position_side or Direction.LONG,
            ):  # type: ignore[arg-type]
                self._exit_trade(price)
                return

            if self.config.sar_enabled:
                try:
                    sig = compute_signal(
                        highs=self._prices,
                        lows=self._prices,
                        closes=self._prices,
                        period=self.config.lookback_intervals,
                        buffer_pct=self.config.entry_buffer_pct,
                    )
                except ValueError:
                    sig = Direction.NONE

                # If opposite signal fire – reverse position
                if (
                    self._position_side == Direction.LONG and sig == Direction.SHORT
                ) or (self._position_side == Direction.SHORT and sig == Direction.LONG):
                    self._exit_trade(price)
                    self._enter_trade(price, sig)

    # ------------------------------------------------------------------
    def _enter_trade(self, price: float, direction: Direction) -> None:
        size = calculate_size(
            capital=100_000,
            risk_per_trade_pct=0.01,
            price=price,
            sl_pct=self.config.sl_pct,
        )
        self.log.info("Entering %s at %.2f, size=%s", direction.name, price, size)
        self._in_position = True
        self._entry_price = price
        self._position_side = direction

    def _exit_trade(self, price: float) -> None:
        # Sign PnL by side
        pnl = price - (self._entry_price or 0.0)
        if self._position_side == Direction.SHORT:
            pnl = -pnl
        self.log.info(
            "Exiting %s at %.2f, PnL=%.2f",
            self._position_side.name if self._position_side else "?",
            price,
            pnl,
        )
        self._in_position = False
        self._entry_price = None
        self._position_side = None

    # ------------------------------------------------------------------
    def on_stop(self):  # noqa: D401,override
        super().on_stop()
        self.log.info("Processed %s quotes in total.", len(self._prices))


__all__ = ["TrendRidingStrategy"]
