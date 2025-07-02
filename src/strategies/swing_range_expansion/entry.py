from __future__ import annotations

import pandas as pd
from enum import Enum
from typing import Tuple

"""Entry signal computation for Swing Range Expansion strategy."""


class Direction(Enum):
    """Trade direction enum."""

    NONE = "NONE"
    LONG = "LONG"
    SHORT = "SHORT"


def compute_nr_mask(high: pd.Series, low: pd.Series, lookback: int) -> pd.Series:
    """Return boolean Series where each True marks an NR*lookback* day.

    Args:
        high: High prices series
        low: Low prices series
        lookback: Number of days to look back for narrowest range

    Returns:
        Boolean series indicating NR days
    """
    ranges = high - low
    rolling_min = ranges.rolling(window=lookback, min_periods=lookback).min()
    # NR day is when today's range equals rolling minimum of last lookback days
    return (ranges == rolling_min) & (~rolling_min.isna())


def compute_breakout_signal(
    current_bar: pd.Series, previous_bar: pd.Series, nr_range: float
) -> Tuple[Direction, float, float, float]:
    """Compute breakout signal from NR day.

    Args:
        current_bar: Current bar data with OHLC
        previous_bar: Previous bar data (the NR day)
        nr_range: The narrow range value

    Returns:
        Tuple of (direction, entry_price, breakout_high, breakout_low)
    """
    if nr_range == 0:
        return Direction.NONE, 0.0, 0.0, 0.0

    breakout_high = previous_bar["high"]
    breakout_low = previous_bar["low"]

    # Check for breakout LONG
    if current_bar["high"] > breakout_high:
        return Direction.LONG, breakout_high, breakout_high, breakout_low

    # Check for breakout SHORT
    if current_bar["low"] < breakout_low:
        return Direction.SHORT, breakout_low, breakout_high, breakout_low

    return Direction.NONE, 0.0, breakout_high, breakout_low


def compute_signal(
    bars: pd.DataFrame, current_index: int, nr_lookback: int
) -> Tuple[Direction, float, float, float, float]:
    """Compute entry signal for current bar.

    Args:
        bars: DataFrame with OHLC data
        current_index: Current bar index
        nr_lookback: Number of days for NR calculation

    Returns:
        Tuple of (direction, entry_price, range_val, breakout_high, breakout_low)
    """
    if current_index < 1:
        return Direction.NONE, 0.0, 0.0, 0.0, 0.0

    current_bar = bars.iloc[current_index]
    previous_bar = bars.iloc[current_index - 1]

    # Check if previous day was an NR day
    nr_mask = compute_nr_mask(bars["high"], bars["low"], nr_lookback)

    if not nr_mask.iloc[current_index - 1]:
        return Direction.NONE, 0.0, 0.0, 0.0, 0.0

    # Calculate the narrow range
    range_val = previous_bar["high"] - previous_bar["low"]

    # Check for breakout
    direction, entry_price, breakout_high, breakout_low = compute_breakout_signal(
        current_bar, previous_bar, range_val
    )

    return direction, entry_price, range_val, breakout_high, breakout_low


__all__ = ["Direction", "compute_signal", "compute_nr_mask", "compute_breakout_signal"]
