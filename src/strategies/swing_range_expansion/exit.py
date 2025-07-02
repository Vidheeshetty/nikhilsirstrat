from __future__ import annotations

import pandas as pd
from typing import Tuple
from .entry import Direction

"""Exit signal computation for Swing Range Expansion strategy."""


class ExitReason:
    """Exit reason constants."""

    STOP_LOSS = "SL"
    TAKE_PROFIT = "TP"
    TIME_LIMIT = "TIME"
    NONE = "NONE"


def compute_exit_prices(
    entry_price: float,
    direction: Direction,
    range_val: float,
    target_rr: float,
    stop_rr: float,
) -> Tuple[float, float]:
    """Compute target and stop prices based on entry and R-multiples.

    Args:
        entry_price: Entry price
        direction: Trade direction (LONG/SHORT)
        range_val: The narrow range value
        target_rr: Target risk-reward ratio
        stop_rr: Stop loss risk-reward ratio

    Returns:
        Tuple of (target_price, stop_price)
    """
    if direction == Direction.LONG:
        target_price = entry_price + target_rr * range_val
        stop_price = entry_price - stop_rr * range_val
    elif direction == Direction.SHORT:
        target_price = entry_price - target_rr * range_val
        stop_price = entry_price + stop_rr * range_val
    else:
        return 0.0, 0.0

    return target_price, stop_price


def check_exit_conditions(
    current_bar: pd.Series,
    direction: Direction,
    target_price: float,
    stop_price: float,
    bars_in_trade: int,
    max_bars_in_trade: int,
) -> Tuple[str, float]:
    """Check if any exit conditions are met.

    Args:
        current_bar: Current bar data
        direction: Trade direction
        target_price: Target price for take profit
        stop_price: Stop loss price
        bars_in_trade: Number of bars in current trade
        max_bars_in_trade: Maximum bars allowed in trade

    Returns:
        Tuple of (exit_reason, exit_price)
    """
    if direction == Direction.LONG:
        # Check stop loss first (risk management priority)
        if current_bar["low"] <= stop_price:
            return ExitReason.STOP_LOSS, stop_price
        # Check take profit
        elif current_bar["high"] >= target_price:
            return ExitReason.TAKE_PROFIT, target_price
        # Check time limit
        elif bars_in_trade >= max_bars_in_trade:
            return ExitReason.TIME_LIMIT, current_bar["close"]

    elif direction == Direction.SHORT:
        # Check stop loss first (risk management priority)
        if current_bar["high"] >= stop_price:
            return ExitReason.STOP_LOSS, stop_price
        # Check take profit
        elif current_bar["low"] <= target_price:
            return ExitReason.TAKE_PROFIT, target_price
        # Check time limit
        elif bars_in_trade >= max_bars_in_trade:
            return ExitReason.TIME_LIMIT, current_bar["close"]

    return ExitReason.NONE, 0.0


def should_exit(
    current_bar: pd.Series,
    direction: Direction,
    entry_price: float,
    range_val: float,
    target_rr: float,
    stop_rr: float,
    bars_in_trade: int,
    max_bars_in_trade: int,
) -> Tuple[bool, str, float]:
    """Check if position should be exited.

    Args:
        current_bar: Current bar data
        direction: Trade direction
        entry_price: Entry price
        range_val: The narrow range value
        target_rr: Target risk-reward ratio
        stop_rr: Stop loss risk-reward ratio
        bars_in_trade: Number of bars in current trade
        max_bars_in_trade: Maximum bars allowed in trade

    Returns:
        Tuple of (should_exit, exit_reason, exit_price)
    """
    target_price, stop_price = compute_exit_prices(
        entry_price, direction, range_val, target_rr, stop_rr
    )

    exit_reason, exit_price = check_exit_conditions(
        current_bar,
        direction,
        target_price,
        stop_price,
        bars_in_trade,
        max_bars_in_trade,
    )

    return exit_reason != ExitReason.NONE, exit_reason, exit_price


__all__ = ["ExitReason", "compute_exit_prices", "check_exit_conditions", "should_exit"]
