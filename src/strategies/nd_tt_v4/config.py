"""Configuration definitions for ND_TT_V4 strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from utils.strategy.base_strategy import StrategyConfigBase


@dataclass
class NdTtV4Config(StrategyConfigBase):
    """Configuration container for ND_TT_V4 strategy."""

    buffer_percentage: float = 0.00001  # 0.001% expressed as decimal
    stop_loss_percentage: float = 0.02  # 2% expressed as decimal
    initial_capital: float = 500_000.0
    order_quantity: float = 1.0  # Number of contracts
    instrument_id: Optional[str] = None
    bar_interval: str = "1-DAY"
    warmup_bars: int = 10
    report_label: str = "ND_TT_V4"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(
        cls, yaml_path: str, *, instrument_id: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None
    ) -> "NdTtV4Config":
        """Build configuration from YAML file with optional overrides."""

        path = Path(yaml_path)
        data: Dict[str, Any] = {}
        if path.exists():
            yaml_data = yaml.safe_load(path.read_text()) or {}
            # Filter out metadata fields that aren't part of the config dataclass
            metadata_fields = {"strategy_name", "description", "version"}
            data = {k: v for k, v in yaml_data.items() if k not in metadata_fields}
        if instrument_id is not None:
            data["instrument_id"] = instrument_id
        if overrides:
            data.update(overrides)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:  # noqa: D401
        base = super().to_dict()
        if "extra" in base and base["extra"] is None:
            base["extra"] = {}
        return base

