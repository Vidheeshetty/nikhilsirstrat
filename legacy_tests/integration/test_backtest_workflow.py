import pytest
from unittest.mock import MagicMock, Mock
from pathlib import Path
import shutil
import os
from datetime import datetime, timezone

# Ensure src is in sys.path for local imports
import sys

current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.config_loader import BacktestConfigLoader
from backtest_utils.data_loader import DataManager
from backtest_utils.engine_launcher import BacktestEngineLauncher
from backtest_utils.results_aggregator import ResultsAggregator
from backtest_utils.report_generator import ReportGenerator


# Mocking MyNSEStrategy and MyNSEStrategyConfig as they are part of the main strategy logic
# and we want to test the runner's integration with them, not their internal logic.
class MockMyNSEStrategyConfig:
    def __init__(self, instrument_id, **kwargs):
        self.instrument_id = instrument_id
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockMyNSEStrategy(Mock):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.log = Mock()
        self.log.info = MagicMock()
        self.log.warning = MagicMock()


# Fixtures for setting up mocked components and dummy data
@pytest.fixture
def mock_config_loader(tmp_path):
    config_file = tmp_path / "mock_config.yaml"
    config_content = """
instrument_id: NIFTY.OPT.19Jun2025.24800.PUT.NSE
start_time: 2025-06-18T09:15:00
end_time: 2025-06-18T09:16:00
catalog_path: {catalog_path}
sl_pct: 0.02
tp_pct: 0.03
"""
    # Will format catalog_path later
    config_file.write_text(config_content)
    mock = Mock(spec=BacktestConfigLoader)
    mock.config_file = str(config_file)
    mock.get_strategy_config = MagicMock(
        side_effect=lambda inst_id: MockMyNSEStrategyConfig(
            inst_id, **mock.config.copy()
        )
    )
    mock.get_backtest_params = MagicMock(
        return_value={
            "start_time": "2025-06-18T09:15:00",
            "end_time": "2025-06-18T09:16:00",
            "base_currency": "INR",
        }
    )
    mock.validate_config = MagicMock(return_value=True)
    # Provide a simple config dict for get_strategy_config to use
    mock.config = {
        "instrument_id": "NIFTY.OPT.19Jun2025.24800.PUT.NSE",
        "start_time": "2025-06-18T09:15:00",
        "end_time": "2025-06-18T09:16:00",
        "catalog_path": "/mock/path/to/catalog",
        "sl_pct": 0.02,
        "tp_pct": 0.03,
    }
    return mock


@pytest.fixture
def mock_data_manager():
    mock = Mock(spec=DataManager)
    mock.get_all_instrument_ids = MagicMock(
        return_value=["NIFTY.OPT.19Jun2025.24800.PUT.NSE"]
    )
    mock.validate_instrument_data = MagicMock(return_value=True)

    # Mock instrument object
    mock_instrument_obj = Mock()
    mock_instrument_obj.id = "NIFTY.OPT.19Jun2025.24800.PUT.NSE"
    mock_instrument_obj.currency = Mock()
    mock_instrument_obj.currency.value = "INR"

    mock.get_instrument = MagicMock(return_value=mock_instrument_obj)

    # Mock quote ticks (simplified)
    mock_ticks = [
        Mock(
            ts_event=dt_to_unix_nanos(
                datetime(2025, 6, 18, 9, 15, 0, tzinfo=timezone.utc)
            )
        ),
        Mock(
            ts_event=dt_to_unix_nanos(
                datetime(2025, 6, 18, 9, 16, 0, tzinfo=timezone.utc)
            )
        ),
    ]
    mock.get_quote_ticks = MagicMock(return_value=mock_ticks)
    return mock


@pytest.fixture
def mock_engine_manager():
    mock = Mock(spec=BacktestEngineLauncher)
    # Mock a minimal NautilusTrader BacktestEngine
    mock_nautilus_engine = Mock()
    mock_nautilus_engine.add_venue = MagicMock()
    mock_nautilus_engine.add_instrument = MagicMock()
    mock_nautilus_engine.add_data = MagicMock()
    mock_nautilus_engine.add_strategy = MagicMock()
    mock_nautilus_engine.run = MagicMock()
    mock_nautilus_engine.get_result = MagicMock(
        return_value=Mock()
    )  # Return a mock result
    mock_nautilus_engine.cache = Mock()  # Ensure cache exists
    mock_nautilus_engine.cache.accounts = MagicMock(return_value=[])
    mock_nautilus_engine.cache.orders = MagicMock(return_value=[])
    mock_nautilus_engine.trader = Mock()
    mock_nautilus_engine.trader.generate_order_fills_report = MagicMock(
        return_value=pd.DataFrame()
    )
    mock_nautilus_engine.trader.generate_positions_report = MagicMock(
        return_value=pd.DataFrame()
    )

    mock.create_engine = MagicMock(return_value=mock_nautilus_engine)
    mock.setup_venue = MagicMock()
    mock.add_instrument = MagicMock()
    mock.add_data = MagicMock()
    mock.add_strategy = MagicMock()
    mock.run_backtest = MagicMock()
    mock.get_results = MagicMock(
        return_value=Mock()
    )  # Should return a mock with relevant attributes
    mock.cleanup = MagicMock()

    # Configure the mock result to have necessary attributes for ResultsProcessor
    mock_result = Mock()
    mock_result.total_orders = 1
    mock_result.total_trades = 1
    mock_result.stats_pnls = {
        "INR": {
            "PnL (total)": 1000.0,
            "PnL% (total)": 0.1,
            "PnL (realized)": 900.0,
            "PnL (unrealized)": 100.0,
            "Sharpe Ratio (252 days)": 1.0,
        }
    }
    mock_result.run_id = "test-run-id"
    mock_result.trader_id = "test-trader-id"
    mock_result.total_return = 0.01
    mock_result.sharpe_ratio = 1.0
    mock_result.max_drawdown = 0.01
    mock_result.total_trades = 1
    mock_result.win_rate = 1.0
    mock_result.elapsed_time = 100
    mock_result.account_balances = pd.DataFrame(
        [{"venue": "NSE", "currency": "INR", "total": 1001000.0}]
    )
    mock_result.realized_pnl = 900.0
    mock_result.unrealized_pnl = 100.0
    mock_result.total_pnl = 1000.0
    mock_result.final_balances = MagicMock(return_value=pd.Series([1001000.0]))

    mock.get_results.return_value = mock_result
    return mock


@pytest.fixture
def mock_results_processor():
    mock = Mock(spec=ResultsAggregator)
    mock.extract_detailed_data = MagicMock(
        return_value={
            "orders": [{"client_order_id": "ORD1"}],
            "positions": [{"id": "POS1"}],
            "trades": [
                {"trade_id": "TRD1", "side": "BUY", "price": "100.0", "quantity": "10"}
            ],
            "account": {
                "starting_balance": 1000000.0,
                "ending_balance": 1001000.0,
                "base_currency": "INR",
            },
            "last_prices": {"NIFTY.OPT.19Jun2025.24800.PUT.NSE": 101.0},
        }
    )
    mock.create_summary_data = MagicMock(
        return_value={
            "instrument_id": "TEST.INSTRUMENT",
            "pnl_total": 1000.0,
            "pnl_pct_total": 0.1,
            "total_orders": 1,
            "total_positions": 1,
            "total_trades": 1,
            "realized_pnl": 900.0,
            "unrealized_pnl": 100.0,
            "sharpe_ratio": 1.0,
            "total_investment": 1000.0,
            "starting_balance": 1000000.0,
            "ending_balance": 1001000.0,
            "balance_free": 1001000.0,
            "balance_locked": 0.0,
            "currency": "INR",
            "base_currency": "INR",
        }
    )
    return mock


@pytest.fixture
def mock_report_generator(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("report_gen_out")
    mock = Mock(spec=ReportGenerator)
    mock.base_dir = str(output_dir)
    mock.write_summary_only = MagicMock()
    mock.print_order_data = MagicMock()
    mock.print_position_data = MagicMock()
    mock.print_trade_data = MagicMock()
    mock.write_batch_results_summary = MagicMock()
    mock.create_consolidated_summary = MagicMock()
    mock.create_tabular_summary = MagicMock()
    return mock


# Import the actual orchestrator for testing
from strategies.my_nse_strategy.runners.backtest.backtest_orchestrator import (
    BacktestOrchestrator,
)


class TestBacktestOrchestratorIntegration:
    def test_run_single_backtest_success(
        self,
        mock_config_loader,
        mock_data_manager,
        mock_engine_manager,
        mock_results_processor,
        mock_report_generator,
        tmp_path,
    ):
        # Configure mocks to work together
        mock_config_loader.config["catalog_path"] = str(
            tmp_path / "dummy_catalog"
        )  # Ensure catalog_path is set
        (
            tmp_path
            / "dummy_catalog"
            / "data"
            / "quote_tick"
            / "NIFTY.OPT.19Jun2025.24800.PUT.NSE"
        ).mkdir(parents=True, exist_ok=True)

        # Patch the Orchestrator's dependencies with our mocks
        # For direct instatiation in test, need to pass mocks to constructor
        orchestrator = BacktestOrchestrator(
            config_file=mock_config_loader.config_file,
            catalog_path=mock_data_manager.catalog_path
            if hasattr(mock_data_manager, "catalog_path")
            else str(tmp_path / "dummy_catalog"),
            base_dir=mock_report_generator.base_dir,
        )

        orchestrator.config_manager = mock_config_loader
        orchestrator.data_manager = mock_data_manager
        orchestrator.engine_manager = mock_engine_manager
        orchestrator.results_processor = mock_results_processor
        orchestrator.report_generator = mock_report_generator

        # Replace MyNSEStrategy import within run_single_backtest with our mock
        orchestrator.MyNSEStrategy = MockMyNSEStrategy

        instrument_id = "NIFTY.OPT.19Jun2025.24800.PUT.NSE"
        start_time = "2025-06-18T09:15:00"
        end_time = "2025-06-18T09:16:00"
        log_file = str(tmp_path / "single_backtest.log")
        verbose = True

        result = orchestrator.run_single_backtest(
            instrument_id=instrument_id,
            start_time=start_time,
            end_time=end_time,
            log_file=log_file,
            verbose=verbose,
            batch_mode=False,
        )

        # Assertions to check if all components were called correctly
        orchestrator.config_manager.validate_config.assert_called_once()
        orchestrator.config_manager.get_strategy_config.assert_called_once_with(
            instrument_id
        )
        orchestrator.config_manager.get_backtest_params.assert_called_once_with(
            start_time, end_time
        )
        orchestrator.data_manager.validate_instrument_data.assert_called_once()
        orchestrator.engine_manager.create_engine.assert_called_once()
        orchestrator.engine_manager.setup_venue.assert_called_once()
        orchestrator.data_manager.get_instrument.assert_called_once()
        orchestrator.engine_manager.add_instrument.assert_called_once()
        orchestrator.data_manager.get_quote_ticks.assert_called_once()
        orchestrator.engine_manager.add_data.assert_called_once()
        orchestrator.engine_manager.add_strategy.assert_called_once()
        orchestrator.engine_manager.run_backtest.assert_called_once()
        orchestrator.engine_manager.get_results.assert_called_once()
        orchestrator.results_processor.extract_detailed_data.assert_called_once()
        orchestrator.results_processor.create_summary_data.assert_called_once()
        orchestrator.report_generator.write_summary_only.assert_called_once()
        orchestrator.report_generator.print_order_data.assert_called_once()
        orchestrator.report_generator.print_position_data.assert_called_once()
        orchestrator.report_generator.print_trade_data.assert_called_once()
        orchestrator.engine_manager.cleanup.assert_called_once()

        assert result["instrument_id"] == "TEST.INSTRUMENT"
        assert Path(log_file).exists()

    def test_run_single_backtest_data_not_available(
        self,
        mock_config_loader,
        mock_data_manager,
        mock_engine_manager,
        mock_results_processor,
        mock_report_generator,
        tmp_path,
    ):
        # Configure data_manager to return False for data availability
        mock_data_manager.validate_instrument_data.return_value = False

        orchestrator = BacktestOrchestrator(
            config_file=mock_config_loader.config_file,
            catalog_path=str(tmp_path / "dummy_catalog"),
            base_dir=mock_report_generator.base_dir,
        )
        orchestrator.config_manager = mock_config_loader
        orchestrator.data_manager = mock_data_manager
        orchestrator.engine_manager = mock_engine_manager
        orchestrator.results_processor = mock_results_processor
        orchestrator.report_generator = mock_report_generator

        with pytest.raises(ValueError, match="No data available for instrument"):
            orchestrator.run_single_backtest(
                instrument_id="NON_EXISTENT.INSTRUMENT",
                start_time="2025-01-01T00:00:00",
                end_time="2025-01-02T00:00:00",
                log_file=None,
                verbose=False,
                batch_mode=False,
            )
        orchestrator.engine_manager.cleanup.assert_called_once()

    # Note: Testing run_batch_backtest and run_all_instruments_backtest directly
    # in an integration test is more complex due to multiprocessing.
    # It's often better to test these at a higher level or with very specific mocks
    # that simulate process pool behavior.
    # For this setup, we assume run_single_backtest_wrapper_for_pool handles the multiprocessing correctly.
    # The primary test for batch processing will be in test_batch_runner_integration.py
