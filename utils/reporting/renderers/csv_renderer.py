from __future__ import annotations

from pathlib import Path
from typing import Any, List, Dict
import pandas as pd

from .base import Renderer


class CsvTradeRenderer(Renderer):
    def render(self, results: List[Dict[str, Any]], out_path: Path) -> None:  # noqa: D401
        rows: List[Dict[str, Any]] = []
        for res in results:
            rows.append(res)
        df = pd.DataFrame(rows)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)


__all__ = ["CsvTradeRenderer"] 