from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import yaml


@dataclass
class BatchConfig:
    instruments: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    near_expiry_only: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path):
        with Path(path).open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(**data)


__all__ = ["BatchConfig"]
