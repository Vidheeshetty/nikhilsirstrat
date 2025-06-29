from __future__ import annotations

"""Configuration objects for TrendRidingStrategy.

This mirrors the pattern used by *MyNSEStrategy*: inherit from
``nautilus_trader.trading.strategy.StrategyConfig`` and declare parameters as
class attributes (no explicit ``__init__``).
"""

from nautilus_trader.trading.strategy import StrategyConfig  # type: ignore
from nautilus_trader.model import InstrumentId


# -----------------------------------------------------------------------------
# Strategy Config
# -----------------------------------------------------------------------------
class TrendRidingStrategyConfig(StrategyConfig):
    """Config parameters for the trend-riding futures strategy."""

    # Core instrument & catalog paths ------------------------------------------------
    instrument_id: InstrumentId  # e.g. "NIFTY_FUT.NSE"
    catalog_path: str = "catalog-data/trend_riding_strategy/catalog"
    meta_catalog_path: str = "catalog-data/trend_riding_strategy/catalog-meta"

    # Basic parameters --------------------------------------------------------------
    lookback_intervals: int = 15  # rolling window length
    sl_pct: float = 0.02  # stop-loss % from entry px
    tp_pct: float = 0.04  # take-profit % from entry px
    position_size: int = 1  # contracts per trade

    # Strategy toggles --------------------------------------------------------------
    sar_enabled: bool = False  # stop-and-reverse flag (future)
    near_expiry_only: bool = False  # process only near-month contracts


__all__ = ["TrendRidingStrategyConfig"]
