from __future__ import annotations

"""Position sizing utilities for trading strategies."""


def calculate_risk_based_size(
    capital: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_price: float,
    min_size: int = 1,
) -> int:
    """Calculate position size based on risk management.

    Args:
        capital: Available capital
        risk_per_trade_pct: Risk per trade as percentage (e.g., 0.01 for 1%)
        entry_price: Entry price
        stop_price: Stop loss price
        min_size: Minimum position size

    Returns:
        Position size (number of units)
    """
    if entry_price <= 0 or stop_price <= 0:
        return min_size

    # Calculate risk per unit
    risk_per_unit = abs(entry_price - stop_price)

    if risk_per_unit == 0:
        return min_size

    # Calculate total risk amount
    total_risk = capital * risk_per_trade_pct

    # Calculate position size
    size = int(total_risk / risk_per_unit)

    return max(size, min_size)


def calculate_fixed_size(
    capital: float, entry_price: float, size_pct: float = 0.1
) -> int:
    """Calculate fixed position size based on capital percentage.

    Args:
        capital: Available capital
        entry_price: Entry price
        size_pct: Percentage of capital to use (e.g., 0.1 for 10%)

    Returns:
        Position size (number of units)
    """
    if entry_price <= 0:
        return 1

    position_value = capital * size_pct
    size = int(position_value / entry_price)

    return max(size, 1)


def calculate_percentage_based_size(
    capital: float,
    price: float,
    sl_pct: float,
    risk_per_trade_pct: float = 0.01,
    min_size: int = 1,
) -> int:
    """Calculate position size based on percentage stop loss.

    Args:
        capital: Available capital
        price: Current price
        sl_pct: Stop loss percentage (e.g., 0.02 for 2%)
        risk_per_trade_pct: Risk per trade as percentage
        min_size: Minimum position size

    Returns:
        Position size (number of units)
    """
    if price <= 0 or sl_pct <= 0:
        return min_size

    # Calculate risk per unit
    risk_per_unit = price * sl_pct

    # Calculate total risk amount
    total_risk = capital * risk_per_trade_pct

    # Calculate position size
    size = int(total_risk / risk_per_unit)

    return max(size, min_size)


__all__ = [
    "calculate_risk_based_size",
    "calculate_fixed_size",
    "calculate_percentage_based_size",
]
