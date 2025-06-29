from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Dict

from .base import Renderer


class JsonTradeRenderer(Renderer):
    def render(self, results: List[Dict[str, Any]], out_path: Path) -> None:  # noqa: D401
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2))


__all__ = ["JsonTradeRenderer"]
