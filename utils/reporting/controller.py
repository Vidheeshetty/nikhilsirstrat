from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import shutil

from .renderers.csv_renderer import CsvTradeRenderer
from .renderers.json_renderer import JsonTradeRenderer
from .renderers.html_batch_renderer import HtmlBatchRenderer

ASSET_SRC = Path(__file__).resolve().parent / "assets"


class ReportController:  # pylint: disable=too-few-public-methods
    """Generate runlogs folder with CSV & JSON reports (HTML later)."""

    def __init__(self, root: Path | str = "runlogs"):
        self.root = Path(root)
        self.csv_renderer = CsvTradeRenderer()
        self.json_renderer = JsonTradeRenderer()
        self.html_renderer = HtmlBatchRenderer()

    # ------------------------------------------------------------------
    def generate(self, results: List[Dict[str, Any]]) -> Path:  # noqa: D401
        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        time_part = now.strftime("%H-%M-%S")

        if len(results) == 1:
            # ----------------------------- INDIVIDUAL RUN --------------------
            inst_id = results[0].get("instrument_id", "UNKNOWN").replace("/", "_")
            out_dir = self.root / "individual" / date_part / time_part
            out_dir.mkdir(parents=True, exist_ok=True)

            assets_dst = out_dir / "assets"
            shutil.copytree(ASSET_SRC, assets_dst, dirs_exist_ok=True)

            # Write CSV/JSON
            self.csv_renderer.render(results, out_dir / f"{inst_id}.csv")
            self.json_renderer.render(results, out_dir / f"{inst_id}.json")

            # Reuse batch HTML summary renderer (single instrument)
            self.html_renderer.render(results, out_dir / f"{inst_id}.html")
            return out_dir

        # ------------------------------- BATCH RUN ---------------------------
        batch_dir = self.root / "batch" / date_part / time_part
        batch_dir.mkdir(parents=True, exist_ok=True)

        assets_dst = batch_dir / "assets"
        shutil.copytree(ASSET_SRC, assets_dst, dirs_exist_ok=True)

        self.csv_renderer.render(results, batch_dir / "trade_details.csv")
        self.json_renderer.render(results, batch_dir / "trade_details.json")
        self.html_renderer.render(results, batch_dir / "summary.html")
        return batch_dir


__all__ = ["ReportController"] 