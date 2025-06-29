import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Ensure src is in sys.path for local imports
import sys

current_dir = Path(__file__).resolve()
project_root = current_dir.parents[2]
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from backtest_utils.engine_launcher import BacktestEngineLauncher
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import Venue, InstrumentId
from nautilus_trader.model.currencies import INR
from nautilus_trader.model.enums import OmsType, AccountType, BookType
from nautilus_trader.model.objects import Money
from nautilus_trader.config import LoggingConfig
import pandas as pd


@pytest.fixture
def mock_engine():
    """Provides a mock BacktestEngine instance."""
    mock = Mock(spec=BacktestEngine)
    mock.add_venue = MagicMock()
    mock.add_instrument = MagicMock()
    mock.add_data = MagicMock()
    mock.add_strategy = MagicMock()
    mock.run = MagicMock()
    mock.get_result = MagicMock()

    # Mock trader and cache for get_results
    mock.trader = Mock()
    mock.trader.generate_positions_report = MagicMock(return_value=pd.DataFrame())
    mock.cache = Mock()
    mock.cache.accounts = MagicMock(return_value=[])
    mock.cache.orders = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_instrument():
    """Provides a mock Instrument object."""
    mock = Mock()
    mock.id = InstrumentId.from_str("TEST.INST.ID")
    return mock


@pytest.fixture
def mock_quote_ticks():
    """Provides mock quote tick data."""
    mock = Mock()
    mock.__len__ = Mock(return_value=100)  # For len(ticks) > 0 check
    return [Mock() for _ in range(5)]  # Simulate a list of ticks


@pytest.fixture
def mock_strategy():
    """Provides a mock Strategy object."""
    mock = Mock()
    return mock


class TestEngineManager:
    def test_create_engine(self):
        manager = BacktestEngineLauncher()
        engine = manager.create_engine()
        assert isinstance(engine, BacktestEngine)
        assert engine.config.trader_id == "BACKTESTER-001"
        assert isinstance(engine.config.logging, LoggingConfig)
        assert engine.config.logging.log_level == "WARNING"

        engine_verbose = manager.create_engine(verbose=True)
        assert engine_verbose.config.logging.log_level == "INFO"

    def test_setup_venue(self, mock_engine):
        manager = BacktestEngineLauncher()
        manager.setup_venue(mock_engine)

        mock_engine.add_venue.assert_called_once()
        args, kwargs = mock_engine.add_venue.call_args
        assert kwargs["venue"] == Venue("NSE")
        assert kwargs["account_type"] == AccountType.MARGIN
        assert kwargs["starting_balances"][0].value == 1_000_000
        assert kwargs["base_currency"] == INR

    def test_add_instrument(self, mock_engine, mock_instrument):
        manager = BacktestEngineLauncher()
        manager.add_instrument(mock_engine, mock_instrument)
        mock_engine.add_instrument.assert_called_once_with(mock_instrument)

    def test_add_data(self, mock_engine, mock_quote_ticks):
        manager = BacktestEngineLauncher()
        manager.add_data(mock_engine, mock_quote_ticks)
        mock_engine.add_data.assert_called_once_with(mock_quote_ticks)

    def test_add_strategy(self, mock_engine, mock_strategy):
        manager = BacktestEngineLauncher()
        manager.add_strategy(mock_engine, mock_strategy)
        mock_engine.add_strategy.assert_called_once_with(mock_strategy)

    def test_run_backtest(self, mock_engine):
        manager = BacktestEngineLauncher()
        manager.run_backtest(mock_engine)
        mock_engine.run.assert_called_once()

    def test_get_results_basic(self, mock_engine):
        manager = BacktestEngineLauncher()
        mock_result = Mock()
        mock_result.account_balances = None  # Simulate initial state
        mock_engine.get_result.return_value = mock_result

        result = manager.get_results(mock_engine)
        assert result is mock_result
        assert hasattr(result, "account_balances")  # Should be added/modified
        assert result.account_balances is not None  # Even if empty DataFrame
        assert hasattr(result, "realized_pnl")
        assert hasattr(result, "unrealized_pnl")
        assert hasattr(result, "total_pnl")

    def test_get_results_with_account_cache(self, mock_engine):
        manager = BacktestEngineLauncher()
        mock_account = Mock()
        mock_account.balance_total = MagicMock(return_value=12345.67)
        mock_account.balance_free = MagicMock(return_value=10000.00)
        mock_account.balance_locked = MagicMock(return_value=2345.67)
        mock_account.account_id = "ACC1"
        mock_account.base_currency = INR
        mock_engine.cache.accounts.return_value = [mock_account]

        mock_result = Mock()
        mock_result.account_balances = None
        mock_engine.get_result.return_value = mock_result

        result = manager.get_results(mock_engine)

        assert result.account_balances is not None
        assert result.account_balances.iloc[0]["total"] == 12345.67
        assert result.account_balances.iloc[0]["currency"] == "INR"

    def test_cleanup(self):
        manager = BacktestEngineLauncher()
        manager.engine = Mock()  # Set a mock engine to be cleaned up
        manager.cleanup()
        assert manager.engine is None

    def test_create_engine_config(self):
        manager = BacktestEngineLauncher()
        config = manager.create_engine_config(
            log_level="DEBUG",
            log_file_path="/tmp/test_log.log",
            bypass_risk_engine=False,
        )

        assert isinstance(config, BacktestEngineConfig)
        assert config.logging.log_level == "DEBUG"
        assert config.logging.log_file_path == "/tmp/test_log.log"
        assert config.risk_engine.bypass == False
        assert config.risk_engine.max_order_submit_rate == "100/00:00:01"
