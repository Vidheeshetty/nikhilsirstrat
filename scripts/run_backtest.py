#!/usr/bin/env python3
"""Universal back-test runner CLI.

Examples
--------
# Single instrument with overrides
python scripts/run_backtest.py --instrument_id NIFTY.FUT.NSE --start_time 2024-01-01

# Multiple instruments (repeat flag)
python scripts/run_backtest.py --instrument_id AAA.FUT.NSE --instrument_id BBB.FUT.NSE

# All instruments in catalog
python scripts/run_backtest.py --instrument_id ALL

# YAML batch file (flags override values inside YAML)
python scripts/run_backtest.py --config config/my_batch.yaml --start_time 2024-01-01
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for p in (ROOT_DIR, SRC_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from utils.data.data_manager import DataManager  # noqa: E402
from utils.runners.batch_config import BatchConfig  # noqa: E402
from strategies.trend_riding.runner.backtest_runner.single_runner import TrendRidingBacktestRunner  # noqa: E402
from strategies.trend_riding.runner.backtest_runner.batch_runner import TrendRidingBatchRunner  # noqa: E402
from utils.reporting.controller import ReportController


def parse_args():
    parser = argparse.ArgumentParser(description="Run Trend-Riding back-test(s)")
    parser.add_argument("--strategy", type=str, default="trend_riding", help="Strategy folder name under src/strategies/")
    parser.add_argument("--instrument_id", action="append", help="Instrument ID (repeatable or ALL)")
    parser.add_argument("--start_time", type=str, default=None)
    parser.add_argument("--end_time", type=str, default=None)
    parser.add_argument("--near_expiry_only", action="store_true")
    parser.add_argument("--config", type=str, help="Optional YAML batch config")
    parser.add_argument("--outfile", type=str, help="Write JSON summary to this path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    strategy_name = args.strategy

    # Merge YAML config if provided
    if args.config:
        cfg = BatchConfig.from_yaml(args.config)
        instruments = args.instrument_id or cfg.instruments or ["ALL"]
        start_time = args.start_time or cfg.start_time
        end_time = args.end_time or cfg.end_time
        near_expiry_only = args.near_expiry_only or cfg.near_expiry_only
    else:
        instruments = args.instrument_id or ["ALL"]
        start_time = args.start_time
        end_time = args.end_time
        near_expiry_only = args.near_expiry_only

    dm = DataManager()
    if instruments == ["ALL"]:
        instruments = dm.get_all_instrument_ids()

    # ------------------------------------------------------------------
    # Dynamically resolve runner classes based on strategy_name
    # ------------------------------------------------------------------
    import importlib

    pkg_root = f"strategies.{strategy_name}.runner.backtest_runner"
    try:
        single_mod = importlib.import_module(f"{pkg_root}.single_runner")
        batch_mod = importlib.import_module(f"{pkg_root}.batch_runner")
    except ModuleNotFoundError as exc:
        sys.exit(f"❌ Could not locate strategy runners for '{strategy_name}': {exc}")

    def _find_cls(mod, suffix: str):
        for attr in getattr(mod, "__all__", []):
            if attr.endswith(suffix):
                return getattr(mod, attr)
        # fallback: scan attributes
        for name in dir(mod):
            if name.endswith(suffix):
                return getattr(mod, name)
        raise AttributeError(f"No class ending with {suffix} found in {mod.__name__}")

    SingleRunnerCls = _find_cls(single_mod, "BacktestRunner")
    BatchRunnerCls = _find_cls(batch_mod, "BatchRunner")

    # Single vs batch route
    if len(instruments) == 1:
        runner = SingleRunnerCls()
        result = runner.run(instruments[0])
        summary = {**result}

        # Generate runlogs even for single-instrument case
        ReportController().generate([result])
    else:
        runner = BatchRunnerCls()
        summary = runner.run(instruments)

    print(json.dumps(summary, indent=2))
    if args.outfile:
        Path(args.outfile).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main() 