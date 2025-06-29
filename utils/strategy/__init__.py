"""Strategy utilities package.

Provides common utilities for trading strategy implementations including:
- Base strategy class
- Technical indicators
- Risk management functions
- Position sizing calculations
- Trade record structures
- Common enums and constants
"""

from .base_strategy import BaseStrategy
from .indicators import sma, ema
from .enums import Direction, ExitReason, OrderSide
from .position import (
    calculate_risk_based_size,
    calculate_fixed_size,
    calculate_percentage_based_size,
)
from .risk import (
    calculate_stop_target_prices_percentage,
    calculate_stop_target_prices_fixed,
    calculate_stop_target_prices_rr,
    is_stop_hit,
    is_target_hit,
    calculate_pnl,
)
from .trades import (
    TradeRecord,
    enrich_trades_with_cumulative_pnl,
    calculate_trade_metrics,
    trades_to_dict_list,
)

__all__ = [
    # Base classes
    "BaseStrategy",
    # Indicators
    "sma",
    "ema",
    # Enums
    "Direction",
    "ExitReason",
    "OrderSide",
    # Position sizing
    "calculate_risk_based_size",
    "calculate_fixed_size",
    "calculate_percentage_based_size",
    # Risk management
    "calculate_stop_target_prices_percentage",
    "calculate_stop_target_prices_fixed",
    "calculate_stop_target_prices_rr",
    "is_stop_hit",
    "is_target_hit",
    "calculate_pnl",
    # Trade records
    "TradeRecord",
    "enrich_trades_with_cumulative_pnl",
    "calculate_trade_metrics",
    "trades_to_dict_list",
]
