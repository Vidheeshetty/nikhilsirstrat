"""Extensive system-level test for report contents.

Run with ``pytest -m system``; skipped by default so that regular CI stays fast.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from utils.reporting.controller import ReportController  # Added missing import

# ------------------------------------------------------------------
# Dependencies required for full-path test
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 1b.  REQUIRE real Nautilus-Trader. If not available, skip the test.
# ------------------------------------------------------------------

try:
    import nautilus_trader  # noqa: F401  pylint: disable=unused-import
except ImportError:
    pytest.skip(
        "Nautilus-Trader not installed – skipping system test", allow_module_level=True
    )

# First, generate a fresh batch run in an isolated tmp directory so the
# assertions below always have up-to-date artifacts.

from utils.data.data_manager import DataManager  # noqa: E402  pylint: disable=wrong-import-position
from strategies.trend_riding.runner.backtest_runner.batch_runner import (
    TrendRidingBatchRunner,  # noqa: E402
)


dm = DataManager()
catalog_ids = dm.get_all_instrument_ids()
if len(catalog_ids) < 2:
    pytest.skip(
        "Not enough instruments in catalog for system test", allow_module_level=True
    )

instruments = catalog_ids[:2]

TrendRidingBatchRunner(max_workers=1).run(instruments)

# ------------------------------------------------------------------
# 2. Locate most-recent batch directory --------------------------------

latest_dir = ReportController.latest_report_dir(
    root=Path("runlogs"), mode="backtesting", run_type="batch"
)
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
assert re.search(r"\d+\.\d{3,}", html_text) is None, (
    "Found value with >2 decimal places in HTML"
)

# c) Trade rows count matches CSV rows
# Count <tr> in Trade Details table (after header row)
trade_table_idx = html_text.find("<h2>Trade Details")
assert trade_table_idx != -1, "Trade Details section missing"
table_html = html_text[trade_table_idx:]
row_count = len(re.findall(r"<tr><td", table_html))
assert row_count == len(df), "Mismatch between CSV and HTML trade rows"
