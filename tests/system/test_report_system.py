"""Extensive system-level test for report contents.

Run with ``pytest -m system``; skipped by default so that regular CI stays fast.
"""

from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

from strategies.trend_riding.runner.backtest_runner.batch_runner import TrendRidingBatchRunner


@pytest.mark.system
def test_trade_report_contents(tmp_path, monkeypatch):
    """Integration test verifying CSV & HTML content integrity."""
    # ------------------------------------------------------------------
    # 1.  Generate fresh batch run (two synthetic instruments) ------------
    instruments = ["AAA.FUT.NSE", "BBB.FUT.NSE"]

    # Monkey-patch *runlogs* root to temp dir so we don't pollute repo output.
    from utils.reporting.controller import ReportController

    def _mock_init(self, root="runlogs"):
        from utils.reporting.renderers.csv_renderer import CsvTradeRenderer
        from utils.reporting.renderers.json_renderer import JsonTradeRenderer
        from utils.reporting.renderers.html_batch_renderer import HtmlBatchRenderer

        self.root = Path(tmp_path) / "runlogs"
        self.csv_renderer = CsvTradeRenderer()
        self.json_renderer = JsonTradeRenderer()
        self.html_renderer = HtmlBatchRenderer()

    monkeypatch.setattr(ReportController, "__init__", _mock_init, raising=True)

    TrendRidingBatchRunner(max_workers=1).run(instruments)

    # ------------------------------------------------------------------
    # 2. Locate latest runlogs/batch directory within tmp_path -----------
    runlogs_batch_root = Path(tmp_path) / "runlogs" / "batch"
    assert runlogs_batch_root.exists(), "Batch reports not generated"

    latest_dir: Path | None = None
    latest_dt = datetime.min

    # Traverse date -> time subfolders
    for date_dir in runlogs_batch_root.iterdir():
        if date_dir.is_dir():
            try:
                date_val = datetime.strptime(date_dir.name, "%Y-%m-%d")
            except ValueError:
                continue
            for time_dir in date_dir.iterdir():
                if time_dir.is_dir():
                    try:
                        ts = datetime.strptime(f"{date_dir.name}_{time_dir.name}", "%Y-%m-%d_%H-%M-%S")
                        if ts > latest_dt:
                            latest_dt = ts
                            latest_dir = time_dir
                    except ValueError:
                        continue

    assert latest_dir is not None, "No batch directory found"

    csv_path = latest_dir / "trade_details.csv"
    html_path = latest_dir / "summary.html"
    assert csv_path.exists(), "CSV report missing"
    assert html_path.exists(), "HTML report missing"

    # ------------------------------------------------------------------
    # 3. CSV validations --------------------------------------------------
    df = pd.read_csv(csv_path)

    # a) Required columns present
    for col in [
        "Instrument",
        "Entry_Price",
        "Exit_Price",
        "Realised_PnL",
        "Trade_Type",
    ]:
        assert col in df.columns, f"Missing column {col}"

    # b) No UNKNOWN instruments
    assert not (df["Instrument"] == "UNKNOWN").any(), "UNKNOWN instrument IDs in CSV"

    # c) Numeric columns rounded to 2 decimals
    for col in df.select_dtypes(include=["float", "float64", "float32"]).columns:
        rounded = df[col].round(2)
        pd.testing.assert_series_equal(df[col], rounded, check_exact=True)

    # ------------------------------------------------------------------
    # 4. HTML validations -------------------------------------------------
    html_text = html_path.read_text()

    # a) No UNKNOWN
    assert "UNKNOWN" not in html_text, "UNKNOWN instrument IDs in HTML"

    # b) Floats do not show >2 decimal places (simple regex heuristic)
    assert re.search(r"\d+\.\d{3,}", html_text) is None, "Found value with >2 decimal places in HTML"

    # c) Trade rows count matches CSV rows
    # Count <tr> in Trade Details table (after header row)
    trade_table_idx = html_text.find("<h2>Trade Details")
    assert trade_table_idx != -1, "Trade Details section missing"
    table_html = html_text[trade_table_idx:]
    row_count = len(re.findall(r"<tr><td", table_html))
    assert row_count == len(df), "Mismatch between CSV and HTML trade rows"