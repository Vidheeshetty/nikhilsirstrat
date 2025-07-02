"""
Base Broker Interface

Abstract base class defining the common interface for all broker integrations.
All broker implementations (Zerodha, Upstox, etc.) must inherit from this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enumeration."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    """Order type enumeration."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"


class TransactionType(Enum):
    """Transaction type enumeration."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BrokerConfig:
    """Base configuration for broker connections."""

    broker_name: str
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    paper_trading: bool = True
    base_url: str = ""
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_second: int = 10

    # Risk management
    max_position_size: int = 100
    max_daily_loss: float = 50000.0
    max_open_positions: int = 10

    # Logging
    log_level: str = "INFO"
    log_orders: bool = True
    log_trades: bool = True


@dataclass
class Order:
    """Order representation."""

    order_id: str
    instrument_id: str
    quantity: int
    price: Optional[float]
    order_type: OrderType
    transaction_type: TransactionType
    status: OrderStatus
    timestamp: datetime
    filled_quantity: int = 0
    average_price: Optional[float] = None
    broker_order_id: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class Position:
    """Position representation."""

    instrument_id: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    unrealized_pnl: float
    timestamp: datetime


@dataclass
class Trade:
    """Trade representation."""

    trade_id: str
    order_id: str
    instrument_id: str
    quantity: int
    price: float
    transaction_type: TransactionType
    timestamp: datetime
    commission: float = 0.0


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.

    This class defines the interface that all broker implementations must follow.
    It provides common functionality and enforces the contract for broker operations.
    """

    def __init__(self, config: BrokerConfig):
        """Initialize the broker with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.broker_name}")
        self.logger.setLevel(getattr(logging, config.log_level))

        self._connected = False
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._trades: List[Trade] = []

        # Callbacks
        self._order_update_callback: Optional[Callable[[Order], None]] = None
        self._trade_callback: Optional[Callable[[Trade], None]] = None
        self._position_update_callback: Optional[Callable[[Position], None]] = None

    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._connected

    @property
    def broker_name(self) -> str:
        """Get broker name."""
        return self.config.broker_name

    # Connection Management
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the broker API."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker API."""
        pass

    # Order Management
    @abstractmethod
    async def place_order(self, order: Order) -> str:
        """
        Place an order with the broker.

        Args:
            order: Order object to place

        Returns:
            Broker order ID
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
    ) -> bool:
        """Modify an existing order."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get current status of an order."""
        pass

    @abstractmethod
    async def get_orders(self) -> List[Order]:
        """Get all orders."""
        pass

    # Position Management
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        pass

    @abstractmethod
    async def get_position(self, instrument_id: str) -> Optional[Position]:
        """Get position for a specific instrument."""
        pass

    # Trade History
    @abstractmethod
    async def get_trades(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """Get trade history."""
        pass

    # Market Data
    @abstractmethod
    async def get_quote(self, instrument_id: str) -> Dict[str, Any]:
        """Get current quote for an instrument."""
        pass

    @abstractmethod
    async def subscribe_quotes(
        self, instrument_ids: List[str], callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Subscribe to real-time quotes."""
        pass

    @abstractmethod
    async def unsubscribe_quotes(self, instrument_ids: List[str]) -> None:
        """Unsubscribe from real-time quotes."""
        pass

    # Account Information
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance and margins."""
        pass

    @abstractmethod
    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get account holdings."""
        pass

    # Callback Registration
    def set_order_update_callback(self, callback: Callable[[Order], None]) -> None:
        """Set callback for order updates."""
        self._order_update_callback = callback

    def set_trade_callback(self, callback: Callable[[Trade], None]) -> None:
        """Set callback for trade updates."""
        self._trade_callback = callback

    def set_position_update_callback(
        self, callback: Callable[[Position], None]
    ) -> None:
        """Set callback for position updates."""
        self._position_update_callback = callback

    # Protected methods for subclasses
    def _notify_order_update(self, order: Order) -> None:
        """Notify order update to registered callback."""
        self._orders[order.order_id] = order
        if self._order_update_callback:
            self._order_update_callback(order)

        if self.config.log_orders:
            self.logger.info(f"Order Update: {order.order_id} - {order.status}")

    def _notify_trade(self, trade: Trade) -> None:
        """Notify trade to registered callback."""
        self._trades.append(trade)
        if self._trade_callback:
            self._trade_callback(trade)

        if self.config.log_trades:
            self.logger.info(
                f"Trade: {trade.trade_id} - {trade.quantity}@{trade.price}"
            )

    def _notify_position_update(self, position: Position) -> None:
        """Notify position update to registered callback."""
        self._positions[position.instrument_id] = position
        if self._position_update_callback:
            self._position_update_callback(position)

    # Utility methods
    def generate_order_id(self) -> str:
        """Generate unique order ID."""
        import uuid

        return f"{self.config.broker_name}_{uuid.uuid4().hex[:8]}"

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on broker connection."""
        try:
            balance = await self.get_account_balance()
            return {
                "status": "healthy",
                "connected": self.is_connected,
                "balance_check": bool(balance),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": self.is_connected,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
