from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml

from utils.strategy.base_strategy import StrategyConfigBase

"""Configuration schema for Trend-Riding strategy.

Provides TrendRidingConfig dataclass that encapsulates all parameters
needed for the strategy, including risk management, position sizing,
and technical analysis settings.

The config can be loaded from YAML files and provides sensible defaults.
"""


@dataclass
class TrendRidingConfig(StrategyConfigBase):
    """Parameters controlling strategy behaviour."""

    # Core instrument & catalog paths ---------------------------------
    instrument_id: str  # e.g. "NIFTY_FUT.NSE"
    catalog_path: str = "catalog-data/trend_riding_strategy/catalog"
    meta_catalog_path: str = "catalog-data/trend_riding_strategy/catalog-meta"

    # Basic parameters -------------------------------------------------
    lookback_intervals: int = 20  # rolling window length (align with strategy spec)
    sl_pct: float = 0.02  # stop-loss % from entry price
    tp_pct: float = 0.04  # take-profit % from entry price
    position_size: int = 1  # contracts per trade

    # Breakout threshold -------------------------------------------------
    # Percentage buffer above previous top (or below previous bottom) that
    # the price must exceed to trigger an entry.  Matches legacy behaviour
    # and feeds into the reported Threshold column.
    entry_buffer_pct: float = 2.0

    # Strategy toggles -------------------------------------------------
    sar_enabled: bool = False  # stop-and-reverse flag (future)
    near_expiry_only: bool = False  # operate only on near-month contracts

    # Backtest specifics (optional overrides) -------------------------
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    # Risk parameters -------------------------------------------------
    # Applied on realised (closed) PnL relative to instrument price at entry.
    max_loss_pct: float = 0.02  # 2 % indices default
    first_day_loss_pct: float = 0.01
    breakeven_shift_pct: float = 0.02  # move SL to entry after +2 %

    # Behaviour -------------------------------------------------------
    instrument_type: str = "INDEX"  # or "STOCK" – doubles buffer/loss caps for stocks

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path, **overrides):  # noqa: D401
        """Build a config from a YAML file.

        Any keys missing in the YAML keep their dataclass defaults, so you
        can specify only the parameters you want to override.
        """
        with Path(path).expanduser().open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        data.update(overrides)
        return cls(**data)


__all__ = ["TrendRidingConfig"]
