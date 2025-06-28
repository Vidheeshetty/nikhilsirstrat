import pytest
import os
from pathlib import Path
import pandas as pd
import shutil

# Ensure src is in sys.path for local imports
import sys
current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.report_generator import ReportGenerator


@pytest.fixture(scope="function")
def report_output_dir(tmp_path_factory):
    """
    Provides a temporary directory for report generation output.
    """
    output_dir = tmp_path_factory.mktemp("report_output")
    return str(output_dir)


@pytest.fixture
def dummy_summary_data():
    """
    Provides dummy summary data for testing ReportGenerator.
    """
    return {
        "instrument_id": "TEST.INSTRUMENT.ID",
        "pnl_total": 12345.67,
        "pnl_pct_total": 1.2345,
        "total_investment": 1000000.00,
        "total_orders": 100,
        "total_positions": 50,
        "total_trades": 75,
        "realized_pnl": 12000.00,
        "unrealized_pnl": 345.67,
        "sharpe_ratio": 1.5678,
        "starting_balance": 1000000.00,
        "ending_balance": 1012345.67,
        "balance_free": 900000.00,
        "balance_locked": 10000.00,
        "currency": "INR",
        "base_currency": "INR",
    }


@pytest.fixture
def dummy_detailed_data():
    """
    Provides dummy detailed data for testing ReportGenerator.
    """
    return {
        "orders": [
            {"client_order_id": "ORD1", "instrument_id": "INST1", "side": "BUY", "quantity": "10", "price": "100.0", "status": "FILLED"},
            {"client_order_id": "ORD2", "instrument_id": "INST1", "side": "SELL", "quantity": "5", "price": "105.0", "status": "FILLED"},
        ],
        "positions": [
            {"id": "POS1", "instrument_id": "INST1", "side": "LONG", "quantity": "5", "avg_px_open": "100.0", "realized_pnl": "500.0"},
        ],
        "trades": [
            {"trade_id": "TRD1", "order_id": "ORD1", "instrument_id": "INST1", "quantity": "10", "price": "100.0"},
            {"trade_id": "TRD2", "order_id": "ORD2", "instrument_id": "INST1", "quantity": "5", "price": "105.0"},
        ],
        "account": {
            "starting_balance": 1000000.00,
            "ending_balance": 1012345.67,
            "balance_free": 900000.00,
            "balance_locked": 10000.00,
            "base_currency": "INR"
        }
    }


@pytest.fixture
def dummy_all_results():
    """
    Provides dummy aggregated results for batch reporting.
    """
    return [
        {
            "instrument_id": "NIFTY.OPT.A",
            "total_orders": 10,
            "total_positions": 5,
            "total_trades": 8,
            "total_investment": "100000.00 INR",
            "pnl_total": "1500.00",
            "pnl_pct_total": "1.5000",
            "realized_pnl": "1400.00",
            "unrealized_pnl": "100.00",
            "sharpe_ratio": "1.2345",
            "starting_balance": 100000.00,
            "ending_balance": 101500.00,
            "balance_free": 90000.00,
            "balance_locked": 5000.00,
            "currency": "INR",
            "base_currency": "INR",
        },
        {
            "instrument_id": "BANKNIFTY.OPT.B",
            "total_orders": 12,
            "total_positions": 6,
            "total_trades": 10,
            "total_investment": "120000.00 INR",
            "pnl_total": "-500.00",
            "pnl_pct_total": "-0.4167",
            "realized_pnl": "-600.00",
            "unrealized_pnl": "100.00",
            "sharpe_ratio": "-0.5000",
            "starting_balance": 100000.00,
            "ending_balance": 99500.00,
            "balance_free": 85000.00,
            "balance_locked": 4000.00,
            "currency": "INR",
            "base_currency": "INR",
        },
    ]


class TestReportGenerator:

    def test_write_summary_only(self, report_output_dir, dummy_summary_data):
        reporter = ReportGenerator(base_dir=report_output_dir)
        log_file = os.path.join(report_output_dir, "test_summary_only.log")
        reporter.write_summary_only(log_file, dummy_summary_data)

        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "BACKTEST RESULTS SUMMARY" in content
        assert "Instrument ID: TEST.INSTRUMENT.ID" in content
        assert "Total PnL: 12,345.67 INR" in content

    def test_print_order_data(self, report_output_dir, dummy_detailed_data):
        reporter = ReportGenerator(base_dir=report_output_dir)
        log_file = os.path.join(report_output_dir, "test_order_data.log")
        reporter.print_order_data(dummy_detailed_data, log_file)

        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "ORDER DATA (2) orders:" in content
        assert "ID=ORD1" in content

    def test_print_position_data(self, report_output_dir, dummy_detailed_data):
        reporter = ReportGenerator(base_dir=report_output_dir)
        log_file = os.path.join(report_output_dir, "test_position_data.log")
        reporter.print_position_data(dummy_detailed_data, log_file)

        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "POSITION DATA (1) positions:" in content
        assert "ID=POS1" in content

    def test_print_trade_data(self, report_output_dir, dummy_detailed_data):
        reporter = ReportGenerator(base_dir=report_output_dir)
        log_file = os.path.join(report_output_dir, "test_trade_data.log")
        reporter.print_trade_data(dummy_detailed_data, log_file)

        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "TRADE DATA (2) trades:" in content
        assert "ID=TRD1" in content

    def test_write_batch_results_summary(self, report_output_dir, dummy_all_results):
        reporter = ReportGenerator(base_dir=report_output_dir)
        log_file = os.path.join(report_output_dir, "test_batch_summary.log")
        reporter.write_batch_results_summary(log_file, dummy_all_results)

        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "BACKTEST RESULTS SUMMARY" in content
        assert "Total PnL: 1000.00 INR" in content  # 1500 - 500
        assert "Sharpe Ratio (avg): 0.3672" in content # (1.2345 + (-0.5000)) / 2

    def test_create_consolidated_summary(self, report_output_dir, dummy_all_results):
        reporter = ReportGenerator(base_dir=report_output_dir)
        output_file = os.path.join(report_output_dir, "test_consolidated_summary.log")
        reporter.create_consolidated_summary(dummy_all_results, output_file)

        assert Path(output_file).exists()
        content = Path(output_file).read_text()
        assert "CONSOLIDATED BACKTEST SUMMARY REPORT" in content
        assert "Total Instruments Tested: 2" in content
        assert "OVERALL SUMMARY" in content
        assert "Total PnL: 1,000.00 INR" in content
        assert "INSTRUMENT-WISE SUMMARY" in content
        assert "NIFTY.OPT.A" in content
        assert "BANKNIFTY.OPT.B" in content

    def test_create_tabular_summary(self, report_output_dir, dummy_all_results):
        reporter = ReportGenerator(base_dir=report_output_dir)
        output_file = os.path.join(report_output_dir, "test_tabular_summary.log")
        reporter.create_tabular_summary(dummy_all_results, output_file)

        assert Path(output_file).exists()
        content = Path(output_file).read_text()
        assert "BACKTEST RESULTS - ALL INSTRUMENTS (TABULAR FORMAT)" in content
        assert "OVERALL SUMMARY" in content
        assert "DETAILED RESULTS BY INSTRUMENT" in content
        assert "NIFTY.OPT.A" in content
        assert "BANKNIFTY.OPT.B" in content 