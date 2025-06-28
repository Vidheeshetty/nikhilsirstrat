from __future__ import annotations

"""Configuration schema for CSV→Parquet conversion utilities."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class ConverterConfig:  # pylint: disable=too-few-public-methods
    """Dataclass capturing all parameters needed for a conversion run."""

    # IO ----------------------------------------------------------------
    source_csv: str
    destination_catalog: str
    destination_meta: str

    # Data description --------------------------------------------------
    data_kind: str = "bar"  # bar | quote | option_chain
    bar_interval: str = "1-DAY"

    # Instrument metadata ----------------------------------------------
    symbol: str = "NIFTY"
    venue: str = "NSE"
    price_precision: int = 2
    price_increment: float = 0.05
    multiplier: int = 1

    # Extra meta fields -------------------------------------------------
    extra_meta_fields: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str | Path) -> "ConverterConfig":
        """Load configuration from YAML file."""
        with Path(path).expanduser().open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(**data)

    def to_dict(self):
        """Return plain dict representation."""
        from dataclasses import asdict
        return asdict(self)


__all__ = ["ConverterConfig"] 