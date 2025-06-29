from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

"""Configuration schema for CSV→Parquet conversion utilities."""


@dataclass
class ConverterConfig:  # pylint: disable=too-few-public-methods
    """Dataclass capturing all parameters needed for a conversion run."""

    # IO ----------------------------------------------------------------
    source_csv: str

    # Either specify a *destination_root* (preferred) or legacy pair of
    # destination_catalog / destination_meta.  If *destination_root* is
    # provided we derive the two sub-folders automatically as
    #   <root>/catalog
    #   <root>/catalog-meta
    destination_root: str | None = None
    destination_catalog: str | None = None  # legacy
    destination_meta: str | None = None  # legacy

    # Whether to wipe the destination catalog before writing. Can be set
    # via CLI --clean flag.
    clean: bool = False

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

    def __post_init__(self):
        """Resolve legacy / new path fields into absolute strings."""
        from string import Template
        import os

        if self.destination_root:
            # Expand env vars & ${VAR} placeholders if any
            root_expanded = Template(self.destination_root).safe_substitute(os.environ)
            self.destination_root = str(Path(root_expanded).expanduser())

            if not self.destination_catalog:
                self.destination_catalog = str(Path(self.destination_root) / "catalog")
            if not self.destination_meta:
                self.destination_meta = str(
                    Path(self.destination_root) / "catalog-meta"
                )

        # Final sanity check
        if not (self.destination_catalog and self.destination_meta):
            raise ValueError(
                "Must specify either destination_root or both destination_catalog & destination_meta"
            )


__all__ = ["ConverterConfig"]
