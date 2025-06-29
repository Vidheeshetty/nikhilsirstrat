#!/usr/bin/env python3
"""
Test script to verify the modularization of the backtest framework.

This script tests that all the new modular components can be imported
and used correctly.
"""

import sys
import os
import re
import pytest
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from backtest_utils.batch_runner import BatchBacktestRunner
from backtest_utils.config_loader import BacktestConfigLoader
from backtest_utils.data_loader import DataManager
from backtest_utils.engine_launcher import BacktestEngineLauncher
from backtest_utils.results_aggregator import ResultsAggregator
from strategies.my_nse_strategy.config_loader import MyNSEStrategyConfigLoader
from strategies.my_nse_strategy.report_generator import MyNSEStrategyReportGenerator
from strategies.my_nse_strategy.strategy import MyNSEStrategy

LOG_DIR = "_summary.txts"
CONFIG_FILE = "config/backtest_config.json"


def _get_valid_instrument_id() -> Optional[str]:
    """
    Finds the first available instrument ID that has data for the configured
    backtest period.
    """
    config_loader = MyNSEStrategyConfigLoader(CONFIG_FILE)
    data_manager = DataManager(config_loader.get("catalog_path"))

    # This will be used by the data_manager to check for data
    backtest_params = config_loader.get_backtest_params()

    instrument_ids = data_manager.get_all_instrument_ids()
    for instrument_id in instrument_ids:
        if data_manager.validate_instrument_data(
            instrument_id, backtest_params["start_time"], backtest_params["end_time"]
        ):
            print(f"Found valid instrument with data: {instrument_id}")
            return instrument_id

    print("Warning: Could not find any instruments with data for the test period.")
    return None


def _run_backtest_directly(
    instrument_id: str, verbose: bool = False, max_workers: int = 1
) -> str:
    """Helper function to run the backtest directly and return the log file content."""
    # Clean up old log files
    if os.path.exists(LOG_DIR):
        for f in os.listdir(LOG_DIR):
            if f.startswith("2025-06") and ("backtest-" in f or "batch-backtest" in f):
                os.remove(os.path.join(LOG_DIR, f))
    else:
        os.makedirs(LOG_DIR)

    config_loader = MyNSEStrategyConfigLoader(CONFIG_FILE)

    engine_launcher = BacktestEngineLauncher()
    results_aggregator = ResultsAggregator()
    report_generator = MyNSEStrategyReportGenerator(LOG_DIR)

    runner = BatchBacktestRunner(
        config_manager=config_loader,
        engine_manager=engine_launcher,
        results_processor=results_aggregator,
        report_generator=report_generator,
    )

    if instrument_id == "all":
        results = runner.run_all_instruments_backtest(
            MyNSEStrategy, verbose=verbose, max_workers=max_workers
        )
    elif instrument_id == "all-top10":
        all_ids = runner.data_manager.get_all_instrument_ids()
        results = runner.run_batch_backtest(
            all_ids[:10], MyNSEStrategy, verbose=verbose, max_workers=max_workers
        )
    else:
        results = runner.run_single_backtest(
            instrument_id, MyNSEStrategy, verbose=verbose
        )

    # Find the newest log file
    log_files = [
        os.path.join(LOG_DIR, f)
        for f in os.listdir(LOG_DIR)
        if f.endswith(".log") or f.endswith(".txt")
    ]
    if not log_files:
        raise FileNotFoundError(
            f"No log file found in {LOG_DIR} for instrument {instrument_id}"
        )

    latest_log_file = max(log_files, key=os.path.getctime)

    with open(latest_log_file, "r") as f:
        content = f.read()
    return content


def test_single_instrument_report_format():
    """Test that the single instrument report has correct formatting for PnL% and Sharpe Ratio."""
    instrument_id = _get_valid_instrument_id()
    if not instrument_id:
        pytest.skip(
            "Could not find any instrument with valid data for the test period."
        )

    print(f"\nTesting single instrument report formatting for {instrument_id}...")
    log_content = _run_backtest_directly(instrument_id)

    assert log_content, "Log file content should not be empty for a successful backtest"
    assert "BACKTEST RESULTS SUMMARY" in log_content
    # Check for PnL percentage formatting
    assert re.search(r"Total PnL %: [-]?\d+\.\d{2}%", log_content)
    # Check for Sharpe ratio formatting
    assert re.search(r"Sharpe Ratio: [-]?\d+\.\d+", log_content)


def test_ten_instruments_batch_report_format():
    """Test that the 10 instruments batch report has correct formatting and totals."""
    print("\nTesting 10 instruments batch report formatting...")
    log_content = _run_backtest_directly("all-top10", max_workers=1)

    # Assertions for batch report format
    assert "CONSOLIDATED BACKTEST SUMMARY REPORT" in log_content
    assert "INSTRUMENT-WISE SUMMARY" in log_content
    assert "TOTAL" in log_content

    data_line_regex = r"^[^|]+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?\d+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?\d+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*$"

    # Find all data lines and extract relevant values (PnL%, Realized, Unrealized, Sharpe)
    all_matches = re.findall(data_line_regex, log_content, re.MULTILINE)
    assert len(all_matches) > 0, "No data lines found in batch report"

    for match_tuple in all_matches:
        # Assuming the order is: Investment, PnL, PnL%, Realized, Unrealized, Sharpe, Start Bal, End Bal
        # Adjust indices if the regex captures differently
        investment_str = match_tuple[0]
        pnl_total_str = match_tuple[1]
        pnl_pct_str = match_tuple[2]
        realized_pnl_str = match_tuple[3]
        unrealized_pnl_str = match_tuple[4]
        sharpe_ratio_str = match_tuple[5]

        # Validate PnL% (group 3 in the regex, index 2 in the tuple)
        if pnl_pct_str != "N/A":
            try:
                float(pnl_pct_str)
            except ValueError:
                assert False, f"PnL% value '{pnl_pct_str}' is not a valid float or N/A"

        # Validate Realized PnL (group 4, index 3)
        if realized_pnl_str != "N/A":
            try:
                float(
                    realized_pnl_str.replace(",", "")
                )  # Remove commas before converting
            except ValueError:
                assert False, (
                    f"Realized PnL value '{realized_pnl_str}' is not a valid float or N/A"
                )

        # Validate Unrealized PnL (group 5, index 4)
        if unrealized_pnl_str != "N/A":
            try:
                float(
                    unrealized_pnl_str.replace(",", "")
                )  # Remove commas before converting
            except ValueError:
                assert False, (
                    f"Unrealized PnL value '{unrealized_pnl_str}' is not a valid float or N/A"
                )

        # Validate Sharpe Ratio (group 6, index 5)
        if sharpe_ratio_str != "N/A":
            try:
                float(sharpe_ratio_str)
            except ValueError:
                assert False, (
                    f"Sharpe Ratio value '{sharpe_ratio_str}' is not a valid float or N/A"
                )

    print("✓ 10 instruments batch report formatting and totals are correct.")


def test_all_instruments_batch_report_format():
    """Test that the all instruments batch report has correct formatting and totals."""
    print("\nTesting all instruments batch report formatting...")
    log_content = _run_backtest_directly("all", max_workers=2)

    # Assertions for batch report format
    assert "CONSOLIDATED BACKTEST SUMMARY REPORT" in log_content
    assert "INSTRUMENT-WISE SUMMARY" in log_content
    assert "TOTAL" in log_content

    data_line_regex = r"^[^|]+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?\d+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?\d+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*\|\s*([-]?[\d,]+\.\d{2}|N/A)\s*$"

    # Find all data lines and extract relevant values (PnL%, Realized, Unrealized, Sharpe)
    all_matches = re.findall(data_line_regex, log_content, re.MULTILINE)
    assert len(all_matches) > 0, "No data lines found in batch report"

    for match_tuple in all_matches:
        # Assuming the order is: Investment, PnL, PnL%, Realized, Unrealized, Sharpe, Start Bal, End Bal
        investment_str = match_tuple[0]
        pnl_total_str = match_tuple[1]
        pnl_pct_str = match_tuple[2]
        realized_pnl_str = match_tuple[3]
        unrealized_pnl_str = match_tuple[4]
        sharpe_ratio_str = match_tuple[5]

        # Validate PnL% (group 3 in the regex, index 2 in the tuple)
        if pnl_pct_str != "N/A":
            try:
                float(pnl_pct_str)
            except ValueError:
                assert False, f"PnL% value '{pnl_pct_str}' is not a valid float or N/A"

        # Validate Realized PnL (group 4, index 3)
        if realized_pnl_str != "N/A":
            try:
                float(
                    realized_pnl_str.replace(",", "")
                )  # Remove commas before converting
            except ValueError:
                assert False, (
                    f"Realized PnL value '{realized_pnl_str}' is not a valid float or N/A"
                )

        # Validate Unrealized PnL (group 5, index 4)
        if unrealized_pnl_str != "N/A":
            try:
                float(
                    unrealized_pnl_str.replace(",", "")
                )  # Remove commas before converting
            except ValueError:
                assert False, (
                    f"Unrealized PnL value '{unrealized_pnl_str}' is not a valid float or N/A"
                )

        # Validate Sharpe Ratio (group 6, index 5)
        if sharpe_ratio_str != "N/A":
            try:
                float(sharpe_ratio_str)
            except ValueError:
                assert False, (
                    f"Sharpe Ratio value '{sharpe_ratio_str}' is not a valid float or N/A"
                )

    print("✓ All instruments batch report formatting and totals are correct.")


def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")

    # Test backtest_utils imports
    from src.backtest_utils import (
        BacktestConfigLoader,
        DataManager,
        BacktestEngineLauncher,
        ResultsAggregator,
        BatchBacktestRunner,
    )

    print("✓ All backtest_utils modules imported successfully")

    # Test strategy imports
    from src.strategies.my_nse_strategy import MyNSEStrategy, MyNSEStrategyConfig

    print("✓ Strategy modules imported successfully")

    # Test runner imports
    print("✓ Backtest runner script path configured successfully")


def test_config_loader():
    """Test the configuration loader functionality."""
    print("\nTesting configuration loader...")

    from src.backtest_utils import BacktestConfigLoader

    # Test loading config
    config_loader = BacktestConfigLoader("config/backtest_config.json")
    config = config_loader.load_config()

    assert config is not None, "Configuration is empty"
    print("✓ Configuration loaded successfully")
    print(f"  - Catalog path: {config.get('catalog_path', 'Not found')}")
    print(f"  - Output dir: {config.get('output_dir', 'Not found')}")


def main():
    """Main function to run all tests."""
    # List of all test functions to run
    tests_to_run = [
        test_imports,
        test_config_loader,
        test_single_instrument_report_format,
        test_ten_instruments_batch_report_format,
        test_all_instruments_batch_report_format,
    ]

    for test_func in tests_to_run:
        try:
            test_func()
        except Exception as e:
            print(f"ERROR in {test_func.__name__}: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
