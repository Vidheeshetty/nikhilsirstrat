from __future__ import annotations

"""Configuration object for the Trend-Riding strategy.

This dataclass replaces the old inheritance model based on Nautilus-Trader
`StrategyConfig`. We keep the parameter names untouched so that existing YAML
files remain compatible, but we drop the heavy import dependency to speed up
unit tests.
"""

from dataclasses import dataclass
from typing import Optional
from utils.strategy.base_strategy import StrategyConfigBase


@dataclass
class TrendRidingConfig(StrategyConfigBase):
    """Parameters controlling strategy behaviour."""

    # Core instrument & catalog paths ---------------------------------
    instrument_id: str  # e.g. "NIFTY_FUT.NSE"
    catalog_path: str = "catalog-data/trend_riding_strategy/catalog"
    meta_catalog_path: str = "catalog-data/trend_riding_strategy/catalog-meta"

    # Basic parameters -------------------------------------------------
    lookback_intervals: int = 15  # rolling window length
    sl_pct: float = 0.02  # stop-loss % from entry price
    tp_pct: float = 0.04  # take-profit % from entry price
    position_size: int = 1  # contracts per trade

    # Strategy toggles -------------------------------------------------
    sar_enabled: bool = False  # stop-and-reverse flag (future)
    near_expiry_only: bool = False  # operate only on near-month contracts

    # Backtest specifics (optional overrides) -------------------------
    start_time: Optional[str] = None
    end_time: Optional[str] = None


__all__ = ["TrendRidingConfig"]
