import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# Ensure src is in sys.path for local imports
import sys

current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.results_aggregator import ResultsAggregator


@pytest.fixture
def dummy_backtest_results_for_aggregator():
    """
    Provides dummy backtest results for testing ResultsAggregator.
    These mimic the 'result' object from NautilusTrader.
    """

    class MockBacktestResult:
        def __init__(
            self,
            total_return,
            total_trades,
            sharpe_ratio,
            win_rate,
            max_drawdown,
            pnl_currency="INR",
        ):
            self.total_return = total_return
            self.total_trades = total_trades
            self.sharpe_ratio = sharpe_ratio
            self.win_rate = win_rate
            self.max_drawdown = max_drawdown
            self.stats_pnls = {
                pnl_currency: {
                    "PnL (total)": float(total_return)
                    * 100000,  # Simulate PnL in currency
                    "PnL% (total)": float(total_return) * 100,
                    "PnL (realized)": float(total_return) * 0.8 * 100000,
                    "PnL (unrealized)": float(total_return) * 0.2 * 100000,
                    "Sharpe Ratio (252 days)": sharpe_ratio,
                }
            }
            self.instrument_id = f"MOCK.INST.{np.random.randint(1000, 9999)}.ID"
            self.base_currency = pnl_currency

    return [
        {"result": MockBacktestResult(0.1, 10, 1.5, 0.6, 0.05, "INR")},
        {"result": MockBacktestResult(0.05, 5, 1.0, 0.7, 0.02, "INR")},
        {"result": MockBacktestResult(0.15, 12, 1.8, 0.65, 0.07, "INR")},
    ]


@pytest.fixture
def dummy_backtest_results_with_failures(dummy_backtest_results_for_aggregator):
    """
    Provides dummy backtest results including some failed runs.
    """
    failures = [
        {
            "error": "Data not found for instrument XXX",
            "instrument_id": "FAILED.INST.1",
        },
        {"error": "Strategy error in instrument YYY", "instrument_id": "FAILED.INST.2"},
    ]
    return dummy_backtest_results_for_aggregator + failures


@pytest.fixture
def dummy_detailed_data():
    """
    Provides dummy detailed data structure as expected by ResultsProcessor.
    """
    return {
        "orders": [],
        "positions": [],
        "trades": [],
        "account": {
            "starting_balance": 100000.0,
            "ending_balance": 105000.0,
            "base_currency": "INR",
        },
        "last_prices": {},  # For unrealized PnL calculation
    }


class TestResultsAggregator:
    def test_aggregate_results_success(self, dummy_backtest_results_for_aggregator):
        aggregator = ResultsAggregator()
        aggregated_results = aggregator.aggregate_results(
            dummy_backtest_results_for_aggregator
        )

        assert aggregated_results["total_runs"] == 3
        assert aggregated_results["successful_runs"] == 3
        assert aggregated_results["failed_runs"] == 0
        assert aggregated_results["avg_return"] == pytest.approx(
            (0.1 + 0.05 + 0.15) / 3
        )
        assert aggregated_results["avg_trades"] == pytest.approx((10 + 5 + 12) / 3)
        assert aggregated_results["sharpe_ratio"] == pytest.approx(
            (1.5 + 1.0 + 1.8) / 3
        )
        assert aggregated_results["win_rate"] == pytest.approx((0.6 + 0.7 + 0.65) / 3)
        # Max drawdown should be the max of absolute values
        assert aggregated_results["max_drawdown"] == max(0.05, 0.02, 0.07)

    def test_aggregate_results_with_failures(
        self, dummy_backtest_results_with_failures
    ):
        aggregator = ResultsAggregator()
        aggregated_results = aggregator.aggregate_results(
            dummy_backtest_results_with_failures
        )

        assert aggregated_results["total_runs"] == 5  # 3 successes + 2 failures
        assert aggregated_results["successful_runs"] == 3
        assert aggregated_results["failed_runs"] == 2
        assert aggregated_results["avg_return"] == pytest.approx(
            (0.1 + 0.05 + 0.15) / 3
        )

    def test_aggregate_results_empty_list(self):
        aggregator = ResultsAggregator()
        aggregated_results = aggregator.aggregate_results([])
        assert aggregated_results == {}

    def test_save_aggregated_results(
        self, dummy_backtest_results_for_aggregator, tmp_path
    ):
        aggregator = ResultsAggregator()
        aggregated = aggregator.aggregate_results(dummy_backtest_results_for_aggregator)

        output_dir = tmp_path / "reports"
        output_dir.mkdir()

        saved_file = aggregator.save_aggregated_results(aggregated, str(output_dir))

        assert Path(saved_file).exists()
        content = Path(saved_file).read_text()
        assert "Aggregated Backtest Results Summary" in content
        assert f"Total Runs: {aggregated['total_runs']}" in content
        assert f"Successful Runs: {aggregated['successful_runs']}" in content
        assert f"Failed Runs: {aggregated['failed_runs']}" in content

    def test_extract_pnl_data_from_stats_pnls(
        self, dummy_backtest_results_for_aggregator, dummy_detailed_data
    ):
        # Use the raw MockBacktestResult directly for this test
        mock_result = dummy_backtest_results_for_aggregator[0]["result"]
        aggregator = ResultsAggregator()
        pnl_data = aggregator.extract_pnl_data(mock_result, dummy_detailed_data)

        assert pnl_data["total_pnl"] == pytest.approx(
            mock_result.stats_pnls["INR"]["PnL (total)"]
        )
        assert pnl_data["pnl_percentage"] == pytest.approx(
            mock_result.stats_pnls["INR"]["PnL% (total)"]
        )
        assert pnl_data["realized_pnl"] == pytest.approx(
            mock_result.stats_pnls["INR"]["PnL (realized)"]
        )
        assert pnl_data["unrealized_pnl"] == pytest.approx(
            mock_result.stats_pnls["INR"]["PnL (unrealized)"]
        )
        assert pnl_data["sharpe_ratio"] == pytest.approx(
            mock_result.stats_pnls["INR"]["Sharpe Ratio (252 days)"]
        )

    def test_calculate_investment(self):
        aggregator = ResultsAggregator()
        trades = [
            {"side": "BUY", "price": "100.0", "quantity": "10"},
            {"side": "SELL", "price": "105.0", "quantity": "5"},
            {"side": "BUY", "price": "90.0", "quantity": "20"},
        ]
        investment = aggregator.calculate_investment(trades)
        assert investment == pytest.approx((100.0 * 10) + (90.0 * 20))

    def test_create_summary_data_single_mode(
        self, dummy_backtest_results_for_aggregator, dummy_detailed_data
    ):
        aggregator = ResultsAggregator()
        mock_result = dummy_backtest_results_for_aggregator[0]["result"]

        # Simulate that there are some trades for investment calculation
        dummy_detailed_data["trades"] = [
            {"side": "BUY", "price": "100.0", "quantity": "10"},
        ]

        summary_data = aggregator.create_summary_data(
            mock_result, dummy_detailed_data, "TEST.INST.ID", batch_mode=False
        )

        assert summary_data["instrument_id"] == "TEST.INST.ID"
        assert summary_data["pnl_total"] == pytest.approx(
            mock_result.stats_pnls["INR"]["PnL (total)"]
        )
        # For single mode, pnl_pct_total is calculated based on total_investment
        assert summary_data["pnl_pct_total"] == pytest.approx(
            (mock_result.stats_pnls["INR"]["PnL (total)"] / 1000.0) * 100
        )
        assert summary_data["total_orders"] == len(dummy_detailed_data["orders"])
        assert summary_data["total_trades"] == len(dummy_detailed_data["trades"])
        assert "starting_balance" in summary_data
        assert "ending_balance" in summary_data

    def test_create_summary_data_batch_mode(
        self, dummy_backtest_results_for_aggregator, dummy_detailed_data
    ):
        aggregator = ResultsAggregator()
        mock_result_dict = dummy_backtest_results_for_aggregator[
            0
        ]  # This is the dict containing "result": MockBacktestResult

        # Add necessary fields to the dictionary for batch_mode handling
        mock_result_dict["total_orders"] = 10
        mock_result_dict["total_positions"] = 5
        mock_result_dict["total_trades"] = 8
        mock_result_dict["detailed_data"] = dummy_detailed_data  # Ensure this is passed
        mock_result_dict["account"] = dummy_detailed_data[
            "account"
        ]  # Ensure this is passed

        # Simulate that there are some trades for investment calculation
        dummy_detailed_data["trades"] = [
            {"side": "BUY", "price": "100.0", "quantity": "10"},
        ]

        summary_data = aggregator.create_summary_data(
            mock_result_dict, dummy_detailed_data, "BATCH.TEST.ID", batch_mode=True
        )

        assert summary_data["instrument_id"] == "BATCH.TEST.ID"
        assert summary_data["total_orders"] == 10
        assert summary_data["total_positions"] == 5
        assert (
            summary_data["total_trades"] == 1
        )  # Based on dummy_detailed_data["trades"]
        assert summary_data["pnl_total"] is not None
        assert summary_data["pnl_pct_total"] is not None
