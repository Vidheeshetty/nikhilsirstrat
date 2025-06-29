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

    def __init__(self, root: Path | str = "runlogs", mode: str = "backtesting"):
        """Initialize ReportController.

        Args:
            root: Root directory for runlogs
            mode: Either 'backtesting' or 'papertrading' to separate report types
        """
        self.root = Path(root) / mode
        self.mode = mode
        self.csv_renderer = CsvTradeRenderer()
        self.json_renderer = JsonTradeRenderer()
        self.html_renderer = HtmlBatchRenderer()

    # ------------------------------------------------------------------
    def generate(
        self,
        results: List[Dict[str, Any]],
        *,
        strategy_name: str | None = None,
    ) -> Path:  # noqa: D401
        """Create run-logs directory and write CSV / JSON / HTML reports.

        The folder layout from v1.2 onwards is::

            runlogs/<mode>/<run_type>/<YYYY-MM-DD>/<HH-MM-SS>_<strategy_name>/

        Where <mode> is either 'backtesting' or 'papertrading', and <run_type>
        is either 'batch' or 'individual'.

        For backward compatibility, *strategy_name* is optional.  When not
        supplied we fall back to the old layout (without suffix).
        """

        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        time_part = now.strftime("%H-%M-%S")

        time_dir_name = f"{time_part}_{strategy_name}" if strategy_name else time_part

        if len(results) == 1:
            # ----------------------------- INDIVIDUAL RUN --------------------
            inst_id = results[0].get("instrument_id", "UNKNOWN").replace("/", "_")
            out_dir = self.root / "individual" / date_part / time_dir_name
            out_dir.mkdir(parents=True, exist_ok=True)

            assets_dst = out_dir / "assets"
            shutil.copytree(ASSET_SRC, assets_dst, dirs_exist_ok=True)

            # Write CSV/JSON
            self.csv_renderer.render(results, out_dir / f"{inst_id}.csv")
            self.json_renderer.render(results, out_dir / f"{inst_id}.json")

            # Reuse batch HTML summary renderer (single instrument)
            self.html_renderer.render(
                results, out_dir / f"{inst_id}.html", strategy_name=strategy_name
            )
            return out_dir

        # ------------------------------- BATCH RUN ---------------------------
        batch_dir = self.root / "batch" / date_part / time_dir_name
        batch_dir.mkdir(parents=True, exist_ok=True)

        assets_dst = batch_dir / "assets"
        shutil.copytree(ASSET_SRC, assets_dst, dirs_exist_ok=True)

        self.csv_renderer.render(results, batch_dir / "trade_details.csv")
        self.json_renderer.render(results, batch_dir / "trade_details.json")
        self.html_renderer.render(
            results, batch_dir / "summary.html", strategy_name=strategy_name
        )
        return batch_dir

    # ------------------------------------------------------------------
    @classmethod
    def latest_report_dir(
        cls,
        root: Path | str = "runlogs",
        mode: str = "backtesting",
        run_type: str = "batch",
    ) -> Path | None:  # noqa: D401
        """Return the most recent report directory for *mode* and *run_type*.

        Args:
            root: Root directory for runlogs
            mode: Either 'backtesting' or 'papertrading'
            run_type: Either 'batch' or 'individual'

        The folder layout is `root/<mode>/<run_type>/YYYY-MM-DD/HH-MM-SS/` as of v1.3.
        Returns `None` if no matching directory is found.
        """
        root_path = Path(root) / mode / run_type
        if not root_path.exists():
            return None

        latest_dt = datetime.min
        latest_path: Path | None = None

        for date_dir in root_path.iterdir():
            if not date_dir.is_dir():
                continue
            try:
                # Validate date part
                datetime.strptime(date_dir.name, "%Y-%m-%d")
            except ValueError:
                continue

            for time_dir in date_dir.iterdir():
                if not time_dir.is_dir():
                    continue
                time_prefix = time_dir.name.split("_", 1)[
                    0
                ]  # drop optional _strategy suffix
                try:
                    ts = datetime.strptime(
                        f"{date_dir.name}_{time_prefix}", "%Y-%m-%d_%H-%M-%S"
                    )
                except ValueError:
                    continue
                if ts > latest_dt:
                    latest_dt = ts
                    latest_path = time_dir

        return latest_path


__all__ = ["ReportController"]
