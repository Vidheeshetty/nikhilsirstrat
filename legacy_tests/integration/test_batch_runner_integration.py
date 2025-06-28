import pytest
from unittest.mock import MagicMock, Mock
from pathlib import Path
import shutil
import os
from datetime import datetime, timezone
import pandas as pd

# Ensure src is in sys.path for local imports
import sys
current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.batch_runner import BatchBacktestRunner


@pytest.fixture
def mock_backtest_orchestrator():
    """
    Provides a mock BacktestOrchestrator for batch runner integration testing.
    """
    mock = Mock()
    # Configure run_single_backtest to return different results for different calls
    # Simulate a successful run and a failed run.
    mock.run_single_backtest.side_effect = [
        # First call: Success
        {
            "instrument_id": "SUCCESS.INST.1",
            "status": "SUCCESS",
            "pnl_total": 1000.0,
            "pnl_pct_total": 0.1,
            "total_trades": 10,
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.05,
            "total_orders": 20,
            "total_positions": 5,
            "realized_pnl": 900.0,
            "unrealized_pnl": 100.0,
            "total_investment": 10000.0,
            "starting_balance": 100000.0,
            "ending_balance": 101000.0,
            "balance_free": 90000.0,
            "balance_locked": 5000.0,
            "currency": "INR",
            "base_currency": "INR",
            "log_file_path": "/tmp/log1.log"
        },
        # Second call: Failure (e.g., data not found)
        {
            "instrument_id": "FAILED.INST.2",
            "status": "FAILED",
            "error": "No data found",
            "log_file_path": "/tmp/log2.log"
        },
        # Third call: Success
        {
            "instrument_id": "SUCCESS.INST.3",
            "status": "SUCCESS",
            "pnl_total": 500.0,
            "pnl_pct_total": 0.05,
            "total_trades": 5,
            "sharpe_ratio": 0.8,
            "max_drawdown": 0.02,
            "total_orders": 10,
            "total_positions": 2,
            "realized_pnl": 400.0,
            "unrealized_pnl": 100.0,
            "total_investment": 5000.0,
            "starting_balance": 100000.0,
            "ending_balance": 100500.0,
            "balance_free": 95000.0,
            "balance_locked": 2000.0,
            "currency": "INR",
            "base_currency": "INR",
            "log_file_path": "/tmp/log3.log"
        },
    ]
    return mock


@pytest.fixture
def mock_report_generator_for_batch(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("batch_report_gen_out")
    mock = Mock()
    mock.base_dir = str(output_dir)
    mock.write_batch_results_summary = MagicMock()
    mock.create_consolidated_summary = MagicMock()
    mock.create_tabular_summary = MagicMock()
    return mock


class TestBatchRunnerIntegration:

    def test_run_batch_backtests(self,
                                  mock_backtest_orchestrator,
                                  mock_report_generator_for_batch,
                                  tmp_path):
        # Dummy list of instruments to process
        instrument_ids = ["SUCCESS.INST.1", "FAILED.INST.2", "SUCCESS.INST.3"]

        # Create a dummy config file for the batch runner
        config_file_path = tmp_path / "batch_config.yaml"
        config_file_path.write_text("""
start_time: 2025-06-18T09:15:00
end_time: 2025-06-18T09:16:00
catalog_path: /mock/catalog/path
""")

        runner = BatchBacktestRunner(
            config_file=str(config_file_path),
            report_path=mock_report_generator_for_batch.base_dir,
            orchestrator=mock_backtest_orchestrator,
            report_generator=mock_report_generator_for_batch
        )

        # Patch the internal orchestrator and report generator with mocks
        runner.orchestrator = mock_backtest_orchestrator
        runner.report_generator = mock_report_generator_for_batch

        runner.run_batch_backtests(instrument_ids, verbose=True)

        # Assertions
        assert mock_backtest_orchestrator.run_single_backtest.call_count == len(instrument_ids)

        # Check calls for each instrument
        call_args = mock_backtest_orchestrator.run_single_backtest.call_args_list
        assert call_args[0].kwargs['instrument_id'] == "SUCCESS.INST.1"
        assert call_args[1].kwargs['instrument_id'] == "FAILED.INST.2"
        assert call_args[2].kwargs['instrument_id'] == "SUCCESS.INST.3"

        # Verify that reports were generated
        mock_report_generator_for_batch.write_batch_results_summary.assert_called_once()
        mock_report_generator_for_batch.create_consolidated_summary.assert_called_once()
        mock_report_generator_for_batch.create_tabular_summary.assert_called_once()

        # Check the aggregated results passed to the report generator (basic check)
        args, kwargs = mock_report_generator_for_batch.write_batch_results_summary.call_args
        assert isinstance(kwargs['summary_data'], dict)
        assert kwargs['summary_data']['total_runs'] == 3
        assert kwargs['summary_data']['successful_runs'] == 2
        assert kwargs['summary_data']['failed_runs'] == 1
        assert kwargs['summary_data']['avg_pnl_total'] == pytest.approx((1000.0 + 500.0) / 2)


    def test_run_all_instruments_backtests(self,
                                           mock_backtest_orchestrator,
                                           mock_report_generator_for_batch,
                                           tmp_path):
        # Configure mock_backtest_orchestrator for more instruments if needed
        # (The side_effect defined in the fixture will handle the first 3)
        mock_backtest_orchestrator.run_single_backtest.side_effect.append({
            "instrument_id": "SUCCESS.INST.4",
            "status": "SUCCESS",
            "pnl_total": 200.0,
            "pnl_pct_total": 0.02,
            "total_trades": 2,
            "sharpe_ratio": 0.5,
            "max_drawdown": 0.01,
            "log_file_path": "/tmp/log4.log"
        })

        # Dummy config file
        config_file_path = tmp_path / "batch_all_config.yaml"
        config_file_path.write_text("""
start_time: 2025-06-18T09:15:00
end_time: 2025-06-18T09:16:00
catalog_path: /mock/catalog/path
""")

        # Mock data_manager to return a list of instrument IDs
        mock_data_manager_for_all = Mock()
        mock_data_manager_for_all.get_all_instrument_ids = MagicMock(return_value=[
            "SUCCESS.INST.1", "FAILED.INST.2", "SUCCESS.INST.3", "SUCCESS.INST.4"
        ])
        mock_data_manager_for_all.catalog_path = "/mock/catalog/path" # Ensure this is set

        runner = BatchBacktestRunner(
            config_file=str(config_file_path),
            report_path=mock_report_generator_for_batch.base_dir,
            orchestrator=mock_backtest_orchestrator,
            report_generator=mock_report_generator_for_batch,
            data_manager=mock_data_manager_for_all
        )
        
        runner.run_all_instruments_backtests(verbose=False)

        # Assertions (similar to run_batch_backtests)
        assert mock_data_manager_for_all.get_all_instrument_ids.called_once()
        assert mock_backtest_orchestrator.run_single_backtest.call_count == 4 # Total calls

        mock_report_generator_for_batch.write_batch_results_summary.assert_called_once()
        mock_report_generator_for_batch.create_consolidated_summary.assert_called_once()
        mock_report_generator_for_batch.create_tabular_summary.assert_called_once() 