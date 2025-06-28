from __future__ import annotations

"""ConfigManager for trend_riding_strategy back-tests.

For Round-1 only supports reading a single YAML file path that contains two
top-level sections:

- strategy: free-form mapping passed verbatim to TrendRidingStrategyConfig
- backtest: with ``start_time`` and ``end_time`` ISO strings
"""

from pathlib import Path
from typing import Any, Dict

import yaml
from strategies.trend_riding_strategy.config import TrendRidingStrategyConfig


class ConfigManager:
    """Lightweight YAML configuration loader."""

    def __init__(self, config_file: str | Path) -> None:
        self.config_file = Path(config_file)
        if not self.config_file.exists():
            raise FileNotFoundError(self.config_file)
        with self.config_file.open() as fh:
            self._raw = yaml.safe_load(fh) or {}

    # ------------------------------------------------------------------
    def validate_config(self) -> None:  # noqa: D401
        """Basic sanity checks."""
        if "strategy" not in self._raw:
            raise ValueError("Config must contain top-level 'strategy' section")

    # ------------------------------------------------------------------
    def get_strategy_config(self, instrument_id: str, **extras: Any) -> TrendRidingStrategyConfig:  # noqa: D401,E501
        cfg: Dict[str, Any] = dict(self._raw.get("strategy", {}))
        cfg.setdefault("instrument_id", instrument_id)
        cfg.update(extras)
        return TrendRidingStrategyConfig(**cfg)

    def get_backtest_params(self, start_time=None, end_time=None) -> Dict[str, Any]:
        bt = self._raw.get("backtest", {})
        return {
            "start_time": start_time or bt.get("start_time"),
            "end_time": end_time or bt.get("end_time"),
        } 