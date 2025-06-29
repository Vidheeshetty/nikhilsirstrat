from __future__ import annotations

from typing import Tuple
from .enums import Direction

"""Risk management utilities for trading strategies."""


def calculate_stop_target_prices_percentage(
    entry_price: float, direction: Direction, stop_pct: float, target_pct: float
) -> Tuple[float, float]:
    """Calculate stop and target prices using percentage-based levels.

    Args:
        entry_price: Entry price
        direction: Trade direction (LONG/SHORT)
        stop_pct: Stop loss percentage (e.g., 0.02 for 2%)
        target_pct: Target profit percentage (e.g., 0.04 for 4%)

    Returns:
        Tuple of (stop_price, target_price)
    """
    if direction == Direction.LONG:
        stop_price = entry_price * (1 - stop_pct)
        target_price = entry_price * (1 + target_pct)
    elif direction == Direction.SHORT:
        stop_price = entry_price * (1 + stop_pct)
        target_price = entry_price * (1 - target_pct)
    else:
        return 0.0, 0.0

    return stop_price, target_price


def calculate_stop_target_prices_fixed(
    entry_price: float, direction: Direction, stop_amount: float, target_amount: float
) -> Tuple[float, float]:
    """Calculate stop and target prices using fixed amounts.

    Args:
        entry_price: Entry price
        direction: Trade direction (LONG/SHORT)
        stop_amount: Stop loss amount (absolute value)
        target_amount: Target profit amount (absolute value)

    Returns:
        Tuple of (stop_price, target_price)
    """
    if direction == Direction.LONG:
        stop_price = entry_price - stop_amount
        target_price = entry_price + target_amount
    elif direction == Direction.SHORT:
        stop_price = entry_price + stop_amount
        target_price = entry_price - target_amount
    else:
        return 0.0, 0.0

    return stop_price, target_price


def calculate_stop_target_prices_rr(
    entry_price: float,
    direction: Direction,
    range_val: float,
    stop_rr: float,
    target_rr: float,
) -> Tuple[float, float]:
    """Calculate stop and target prices using risk-reward ratios.

    Args:
        entry_price: Entry price
        direction: Trade direction (LONG/SHORT)
        range_val: Base range value (e.g., ATR, narrow range)
        stop_rr: Stop loss risk-reward ratio
        target_rr: Target profit risk-reward ratio

    Returns:
        Tuple of (stop_price, target_price)
    """
    if direction == Direction.LONG:
        stop_price = entry_price - stop_rr * range_val
        target_price = entry_price + target_rr * range_val
    elif direction == Direction.SHORT:
        stop_price = entry_price + stop_rr * range_val
        target_price = entry_price - target_rr * range_val
    else:
        return 0.0, 0.0

    return stop_price, target_price


def is_stop_hit(
    current_price: float, entry_price: float, direction: Direction, stop_pct: float
) -> bool:
    """Check if percentage-based stop loss is hit.

    Args:
        current_price: Current market price
        entry_price: Entry price
        direction: Trade direction
        stop_pct: Stop loss percentage

    Returns:
        True if stop loss is hit
    """
    if direction == Direction.LONG:
        return current_price <= entry_price * (1 - stop_pct)
    elif direction == Direction.SHORT:
        return current_price >= entry_price * (1 + stop_pct)
    return False


def is_target_hit(
    current_price: float, entry_price: float, direction: Direction, target_pct: float
) -> bool:
    """Check if percentage-based target profit is hit.

    Args:
        current_price: Current market price
        entry_price: Entry price
        direction: Trade direction
        target_pct: Target profit percentage

    Returns:
        True if target profit is hit
    """
    if direction == Direction.LONG:
        return current_price >= entry_price * (1 + target_pct)
    elif direction == Direction.SHORT:
        return current_price <= entry_price * (1 - target_pct)
    return False


def calculate_pnl(
    entry_price: float, exit_price: float, direction: Direction, position_size: int = 1
) -> float:
    """Calculate profit/loss for a trade.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        direction: Trade direction
        position_size: Position size (number of units)

    Returns:
        Profit/loss amount
    """
    raw_pnl = exit_price - entry_price
    if direction == Direction.SHORT:
        raw_pnl = -raw_pnl
    return raw_pnl * position_size


__all__ = [
    "calculate_stop_target_prices_percentage",
    "calculate_stop_target_prices_fixed",
    "calculate_stop_target_prices_rr",
    "is_stop_hit",
    "is_target_hit",
    "calculate_pnl",
]
