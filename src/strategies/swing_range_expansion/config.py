from __future__ import annotations

import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

"""Configuration schema for Swing Range Expansion strategy."""


@dataclass(slots=True)
class SwingRangeConfig:  # pylint: disable=too-many-instance-attributes
    """All tunable parameters with safe defaults.

    Users may override any field via YAML or keyword arguments.
    """

    nr_lookback: int = 7  # Days to test for narrowest range
    target_rr: float = 1.5  # × NR range for take-profit
    stop_rr: float = 0.75  # × NR range for stop-loss
    max_bars_in_trade: int = 3  # Exit after N bars regardless

    timeframe: str = "INTERDAY"  # For future data fetchers
    interval: str = "DAILY"

    instrument_id: str | None = None  # Filled by runner if absent

    # ------------------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str | Path, **overrides: Any) -> "SwingRangeConfig":  # noqa: D401
        """Load config from *path* if it exists.

        Any keyword overrides take precedence over YAML and defaults.
        """
        path = Path(path)
        data: Dict[str, Any] = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)

    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:  # noqa: D401
        """Return dict representation (useful for experiment tracking)."""
        return asdict(self)


__all__ = ["SwingRangeConfig"]
