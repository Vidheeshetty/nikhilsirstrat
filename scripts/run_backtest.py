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
from utils.reporting.controller import ReportController  # noqa: E402


def load_default_config():
    """Load default configuration from config/backtest_config.json."""
    config_path = ROOT_DIR / "config" / "backtest_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def parse_args():
    parser = argparse.ArgumentParser(description="Run Trend-Riding back-test(s)")
    parser.add_argument(
        "--strategy",
        type=str,
        default="trend_riding",
        help="Strategy folder name under src/strategies/",
    )
    parser.add_argument(
        "--instrument_id", action="append", help="Instrument ID (repeatable or ALL)"
    )
    parser.add_argument("--start_time", type=str, default=None)
    parser.add_argument("--end_time", type=str, default=None)
    parser.add_argument("--near_expiry_only", action="store_true")
    parser.add_argument("--config", type=str, help="Optional YAML batch config")
    parser.add_argument("--outfile", type=str, help="Write JSON summary to this path")
    parser.add_argument(
        "--catalog_path", type=str, help="Override Parquet catalog root(s)"
    )
    parser.add_argument(
        "--bar_interval",
        type=str,
        default="1-DAY",
        help="Bar interval in catalog, e.g., 1-DAY or 1-MINUTE",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load default configuration
    default_config = load_default_config()
    default_catalog_path = default_config.get("catalog_path")

    strategy_name = args.strategy

    # Merge YAML config if provided
    if args.config:
        cfg = BatchConfig.from_yaml(args.config)
        instruments = args.instrument_id or cfg.instruments or ["ALL"]
        # Note: start_time, end_time, near_expiry_only are parsed but not yet used by runners
        # They are reserved for future filtering/date-range functionality
        _ = args.start_time or cfg.start_time
        _ = args.end_time or cfg.end_time
        _ = args.near_expiry_only or cfg.near_expiry_only
    else:
        instruments = args.instrument_id or ["ALL"]
        # Note: These parameters are parsed but not yet implemented in the runner
        _ = args.start_time
        _ = args.end_time
        _ = args.near_expiry_only

    # Use provided catalog_path or fall back to default from config
    catalog_path = args.catalog_path or default_catalog_path

    # Propagate catalog path to any deeper DataManager instances created by
    # strategy runners.  The shared environment variable means we don't have
    # to plumb the argument through every call-stack layer.
    if catalog_path:
        import os

        os.environ["DATA_CATALOG_ROOTS"] = catalog_path

    # Export bar_interval so downstream renderers can derive data period
    os.environ["BAR_INTERVAL"] = args.bar_interval.upper()

    dm = DataManager(catalog_path=catalog_path, bar_interval=args.bar_interval)
    if len(instruments) == 1 and instruments[0].upper() == "ALL":
        instruments = dm.get_all_instrument_ids()

    # ------------------------------------------------------------------
    # Dynamically resolve runner classes based on strategy_name
    # ------------------------------------------------------------------
    import importlib

    pkg_root = f"strategies.{strategy_name}.runner.backtest_runner"
    try:
        single_mod = importlib.import_module(f"{pkg_root}.single_runner")
    except ModuleNotFoundError:
        # Fallback to single file `backtest_runner.py`
        single_mod = importlib.import_module(f"{pkg_root}")

    try:
        batch_mod = importlib.import_module(f"{pkg_root}.batch_runner")
    except ModuleNotFoundError:
        # Some strategies only ship a single-runner; we create a simple batch
        # wrapper on the fly.
        class _DefaultBatchRunner:  # type: ignore
            def __init__(self, runner_cls):
                self._runner = runner_cls()

            def run(self, instruments):
                results = [self._runner.run(instr) for instr in instruments]
                from utils.runners.base_batch_runner import BatchRunner as _Agg

                agg = _Agg.aggregate(results)
                agg["results"] = results
                from utils.reporting.controller import ReportController

                ReportController(mode="backtesting").generate(
                    results, strategy_name=strategy_name
                )
                return agg

        batch_mod = None  # placeholder; we'll supply class later

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
    if batch_mod:
        BatchRunnerCls = _find_cls(batch_mod, "BatchRunner")
    else:
        # Dynamically create batch runner wrapper class
        class BatchRunnerCls(_DefaultBatchRunner):  # type: ignore
            def __init__(self):
                super().__init__(SingleRunnerCls)

    # Single vs batch route
    if len(instruments) == 1:
        runner = SingleRunnerCls()
        result = runner.run(instruments[0])
        summary = {**result}

        # Generate runlogs even for single-instrument case
        ReportController(mode="backtesting").generate(
            [result], strategy_name=strategy_name
        )
    else:
        runner = BatchRunnerCls()
        summary = runner.run(instruments)

    print(json.dumps(summary, indent=2))
    if args.outfile:
        Path(args.outfile).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
