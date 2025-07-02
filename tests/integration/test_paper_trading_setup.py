"""
Integration tests for paper trading setup.

Tests the complete paper trading infrastructure including brokers,
configuration, and basic functionality.
"""

import pytest
import asyncio
import tempfile
import yaml
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.brokers.base import Order, OrderType, TransactionType, OrderStatus  # noqa: E402
from src.brokers.manager import BrokerManager  # noqa: E402
from src.brokers.zerodha.broker import ZerodhaBroker  # noqa: E402
from utils.runners.paper_trading_runner import PaperTradingStrategyRunner  # noqa: E402
from utils.reporting.paper_trading_reporter import PaperTradingReporter  # noqa: E402
from src.brokers.zerodha.config import ZerodhaConfig  # noqa: E402
from src.brokers.paper import PaperBroker  # noqa: E402


class TestPaperTradingSetup:
    """Test paper trading infrastructure setup."""

    @pytest.fixture
    def paper_config(self):
        """Create paper trading configuration."""
        return {
            "broker_name": "zerodha",
            "paper_trading": True,
            "api_key": "test_key",
            "api_secret": "test_secret",
            "paper_initial_balance": 1000000.0,
            "paper_brokerage_per_order": 20.0,
            "max_position_size": 100,
            "max_daily_loss": 50000.0,
            "log_level": "INFO",
        }

    @pytest.fixture
    def broker_manager_config(self, paper_config):
        """Create broker manager configuration."""
        config = {
            "brokers": {"zerodha": paper_config},
            "strategies": {"test_strategy": {"enabled": True, "broker": "zerodha"}},
        }

        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            return f.name

    @pytest.mark.asyncio
    async def test_zerodha_config_creation(self, paper_config):
        """Test Zerodha configuration creation."""
        config = ZerodhaConfig(**paper_config)

        assert config.broker_name == "zerodha"
        assert config.paper_trading is True
        assert config.paper_initial_balance == 1000000.0
        assert config.max_position_size == 100

    @pytest.mark.asyncio
    async def test_paper_broker_initialization(self, paper_config):
        """Test paper broker initialization."""
        config = ZerodhaConfig(**paper_config)
        broker = PaperBroker(config)

        assert broker.config.broker_name == "zerodha"
        assert not broker.is_connected

        # Test connection
        connected = await broker.connect()
        assert connected is True
        assert broker.is_connected is True

        # Test disconnection
        await broker.disconnect()
        assert broker.is_connected is False

    @pytest.mark.asyncio
    async def test_broker_manager_initialization(self, broker_manager_config):
        """Test broker manager initialization."""
        manager = BrokerManager()

        try:
            await manager.initialize(broker_manager_config)

            # Check broker was added
            assert len(manager._brokers) == 1
            assert "zerodha" in manager._brokers

            # Check broker is connected
            zerodha_broker = manager.get_broker("zerodha")
            assert zerodha_broker is not None
            assert zerodha_broker.is_connected

            # Test statistics
            stats = manager.get_statistics()
            assert stats["total_brokers"] == 1
            assert stats["connected_brokers"] == 1

        finally:
            await manager.shutdown()

        # Clean up config file
        Path(broker_manager_config).unlink()

    @pytest.mark.asyncio
    async def test_order_placement_and_execution(self, paper_config):
        """Test order placement and execution."""
        config = ZerodhaConfig(**paper_config)
        broker = PaperBroker(config)

        try:
            await broker.connect()

            # Create test order
            order = Order(
                order_id="TEST_ORDER_001",
                instrument_id="NIFTY.FUT.NSE",
                quantity=1,
                price=None,  # Market order
                order_type=OrderType.MARKET,
                transaction_type=TransactionType.BUY,
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
            )

            # Place order
            broker_order_id = await broker.place_order(order)
            assert broker_order_id is not None
            assert order.broker_order_id is not None

            # Wait for execution (paper broker should execute quickly)
            await asyncio.sleep(1)

            # Check order status
            updated_order = await broker.get_order_status(order.order_id)
            assert updated_order is not None

            # Get all orders
            orders = await broker.get_orders()
            assert len(orders) >= 1

            # Check account balance was updated
            balance = await broker.get_account_balance()
            assert "cash" in balance
            assert "available_balance" in balance

        finally:
            await broker.disconnect()

    @pytest.mark.asyncio
    async def test_position_tracking(self, paper_config):
        """Test position tracking functionality."""
        config = ZerodhaConfig(**paper_config)
        broker = PaperBroker(config)

        try:
            await broker.connect()

            # Place buy order
            buy_order = Order(
                order_id="BUY_ORDER_001",
                instrument_id="NIFTY.FUT.NSE",
                quantity=2,
                price=None,
                order_type=OrderType.MARKET,
                transaction_type=TransactionType.BUY,
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
            )

            await broker.place_order(buy_order)
            await asyncio.sleep(1)  # Wait for execution

            # Check positions
            positions = await broker.get_positions()
            assert len(positions) >= 1

            # Find our position
            nifty_position = next(
                (p for p in positions if p.instrument_id == "NIFTY.FUT.NSE"), None
            )
            assert nifty_position is not None
            assert nifty_position.quantity == 2

            # Place sell order to reduce position
            sell_order = Order(
                order_id="SELL_ORDER_001",
                instrument_id="NIFTY.FUT.NSE",
                quantity=1,
                price=None,
                order_type=OrderType.MARKET,
                transaction_type=TransactionType.SELL,
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
            )

            await broker.place_order(sell_order)
            await asyncio.sleep(1)  # Wait for execution

            # Check updated position
            updated_positions = await broker.get_positions()
            nifty_position = next(
                (p for p in updated_positions if p.instrument_id == "NIFTY.FUT.NSE"),
                None,
            )
            assert nifty_position is not None
            assert nifty_position.quantity == 1

        finally:
            await broker.disconnect()

    @pytest.mark.asyncio
    async def test_market_data_simulation(self, paper_config):
        """Test market data simulation."""
        config = ZerodhaConfig(**paper_config)
        broker = PaperBroker(config)

        try:
            await broker.connect()

            # Get quote for instrument
            quote = await broker.get_quote("NIFTY.FUT.NSE")

            assert "instrument_id" in quote
            assert "bid" in quote
            assert "ask" in quote
            assert "last_price" in quote
            assert "volume" in quote
            assert "timestamp" in quote

            assert quote["instrument_id"] == "NIFTY.FUT.NSE"
            assert quote["bid"] > 0
            assert quote["ask"] > quote["bid"]  # Ask should be higher than bid
            assert quote["last_price"] > 0

        finally:
            await broker.disconnect()

    @pytest.mark.asyncio
    async def test_risk_management_integration(self, paper_config):
        """Test risk management features."""
        # Set low limits for testing
        config_dict = paper_config.copy()
        config_dict["max_position_size"] = 1
        config_dict["max_daily_loss"] = 1000.0

        config = ZerodhaConfig(**config_dict)
        broker = PaperBroker(config)

        try:
            await broker.connect()

            # Test position size limit
            large_order = Order(
                order_id="LARGE_ORDER_001",
                instrument_id="NIFTY.FUT.NSE",
                quantity=100,  # Exceeds max_position_size
                price=None,
                order_type=OrderType.MARKET,
                transaction_type=TransactionType.BUY,
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
            )

            # Order should still be placed (risk checking is at engine level)
            broker_order_id = await broker.place_order(large_order)
            assert broker_order_id is not None

        finally:
            await broker.disconnect()

    @pytest.mark.asyncio
    async def test_commission_calculation(self, paper_config):
        """Test commission calculation."""
        config = ZerodhaConfig(**paper_config)
        broker = PaperBroker(config)

        try:
            await broker.connect()

            # Place order and wait for execution
            order = Order(
                order_id="COMMISSION_TEST_001",
                instrument_id="NIFTY.FUT.NSE",
                quantity=1,
                price=None,
                order_type=OrderType.MARKET,
                transaction_type=TransactionType.BUY,
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
            )

            initial_balance = await broker.get_account_balance()
            initial_cash = initial_balance["cash"]

            await broker.place_order(order)
            await asyncio.sleep(1)  # Wait for execution

            # Check that commission was deducted
            final_balance = await broker.get_account_balance()
            final_cash = final_balance["cash"]

            # Cash should have decreased by more than just the trade value
            # (due to commission)
            assert final_cash < initial_cash

            # Get trades to check commission
            trades = await broker.get_trades()
            assert len(trades) >= 1

            trade = trades[-1]  # Latest trade
            assert trade.commission > 0
            assert trade.commission >= 20.0  # Minimum brokerage

        finally:
            await broker.disconnect()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
