#!/usr/bin/env python3
"""CLI wrapper to run Trend-Riding batch back-tests.

Example:
    python scripts/run_batch_backtest.py --instruments AAA.FUT.NSE BBB.FUT.NSE
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make local repo importable when executed directly --------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Also inject src/ for absolute imports like `strategies.*`
SRC_DIR = ROOT_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from strategies.trend_riding.runner.backtest_runner.batch_runner import (  # noqa: E402
    TrendRidingBatchRunner,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Trend-Riding batch back-test")
    parser.add_argument(
        "--instruments", nargs="*", required=True, help="Instrument IDs to back-test"
    )
    parser.add_argument(
        "--outfile", type=str, default=None, help="Optional JSON output path"
    )
    args = parser.parse_args()

    runner = TrendRidingBatchRunner()
    summary = runner.run(args.instruments)

    print(json.dumps(summary, indent=2))
    if args.outfile:
        out_path = Path(args.outfile)
        out_path.write_text(json.dumps(summary, indent=2))
        import sys as _sys

        print(f"Results written to {out_path}", file=_sys.stderr)


if __name__ == "__main__":
    main()
