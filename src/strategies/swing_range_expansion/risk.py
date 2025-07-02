from __future__ import annotations

from .entry import Direction

"""Risk management for Swing Range Expansion strategy."""


class RiskManager:
    """Risk management for position exits."""

    def __init__(self, stop_rr: float, target_rr: float):
        """Initialize risk manager.

        Args:
            stop_rr: Stop loss risk-reward ratio
            target_rr: Target profit risk-reward ratio
        """
        self.stop_rr = stop_rr
        self.target_rr = target_rr

    def hit(
        self,
        current_price: float,
        entry_price: float,
        range_val: float,
        side: Direction,
    ) -> bool:
        """Check if stop loss or take profit is hit.

        Args:
            current_price: Current market price
            entry_price: Entry price
            range_val: The narrow range value
            side: Position side (LONG/SHORT)

        Returns:
            True if stop loss or take profit is hit
        """
        if side == Direction.LONG:
            stop_price = entry_price - self.stop_rr * range_val
            target_price = entry_price + self.target_rr * range_val
            return current_price <= stop_price or current_price >= target_price
        elif side == Direction.SHORT:
            stop_price = entry_price + self.stop_rr * range_val
            target_price = entry_price - self.target_rr * range_val
            return current_price >= stop_price or current_price <= target_price

        return False

    def get_exit_prices(
        self, entry_price: float, range_val: float, side: Direction
    ) -> tuple[float, float]:
        """Get stop loss and target prices.

        Args:
            entry_price: Entry price
            range_val: The narrow range value
            side: Position side (LONG/SHORT)

        Returns:
            Tuple of (stop_price, target_price)
        """
        if side == Direction.LONG:
            stop_price = entry_price - self.stop_rr * range_val
            target_price = entry_price + self.target_rr * range_val
        elif side == Direction.SHORT:
            stop_price = entry_price + self.stop_rr * range_val
            target_price = entry_price - self.target_rr * range_val
        else:
            return 0.0, 0.0

        return stop_price, target_price


__all__ = ["RiskManager"]
