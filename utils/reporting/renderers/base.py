from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Dict


class Renderer(ABC):
    @abstractmethod
    def render(self, results: List[Dict[str, Any]], out_path: Path) -> None:  # noqa: D401
        """Render *results* to *out_path* (write file to disk)."""
