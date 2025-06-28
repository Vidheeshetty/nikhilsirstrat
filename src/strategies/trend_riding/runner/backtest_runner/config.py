from __future__ import annotations

"""Backtest runner configuration (placeholder)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BacktestRunnerConfig:  # pylint: disable=too-few-public-methods
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    slippage_bps: float = 0.0
    fees_per_contract: float = 0.0


__all__ = ["BacktestRunnerConfig"]
