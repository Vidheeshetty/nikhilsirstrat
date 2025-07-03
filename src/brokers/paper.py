"""
Paper Trading Broker

Simulates real broker functionality for paper trading.
Provides realistic order execution, position tracking, and market simulation.
"""

import asyncio
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import logging
import uuid

from .base import (
    BaseBroker,
    BrokerConfig,
    Order,
    Position,
    Trade,
    OrderStatus,
    OrderType,
    TransactionType,
)

logger = logging.getLogger(__name__)


class PaperBroker(BaseBroker):
    """
    Paper trading broker implementation.

    Simulates real broker functionality including:
    - Order execution with realistic delays
    - Position tracking and P&L calculation
    - Market data simulation
    - Commission and slippage modeling
    """

    def __init__(self, config: BrokerConfig):
        """Initialize paper broker."""
        super().__init__(config)

        # Paper trading state
        self._account_balance = getattr(config, "paper_initial_balance", 1000000.0)
        self._initial_balance = self._account_balance
        self._used_margin = 0.0
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0

        # Market simulation
        self._market_prices: Dict[str, float] = {}
        self._price_history: Dict[str, List[float]] = {}
        self._volatility: Dict[str, float] = {}

        # Order execution simulation
        self._execution_delay_range = (0.1, 0.5)  # seconds
        self._slippage_range = (0.0, 0.02)  # percentage
        self._fill_probability = 0.98  # 98% fill rate

        # Commission structure (Zerodha-like)
        self._brokerage_per_order = getattr(config, "paper_brokerage_per_order", 20.0)
        self._stt_rate = getattr(config, "paper_stt_rate", 0.025) / 100
        self._transaction_charges = (
            getattr(config, "paper_transaction_charges", 0.00325) / 100
        )

        # Background tasks
        self._market_update_task: Optional[asyncio.Task] = None
        self._order_processing_task: Optional[asyncio.Task] = None

        self.logger.info(
            f"Paper broker initialized with balance: ₹{self._account_balance:,.2f}"
        )

    async def connect(self) -> bool:
        """Connect to paper trading system."""
        try:
            self._connected = True

            # Start background tasks - ensure we have an event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, this shouldn't happen in async context
                self.logger.error("No event loop running when connecting paper broker")
                return False

            # Start background tasks
            self._market_update_task = asyncio.create_task(self._market_update_loop())
            self._order_processing_task = asyncio.create_task(
                self._order_processing_loop()
            )

            self.logger.info("Paper broker connected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect paper broker: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from paper trading system."""
        self._connected = False

        # Cancel background tasks
        if self._market_update_task:
            self._market_update_task.cancel()
        if self._order_processing_task:
            self._order_processing_task.cancel()

        self.logger.info("Paper broker disconnected")

    async def place_order(self, order: Order) -> str:
        """Place an order in the paper trading system."""
        if not self._connected:
            raise RuntimeError("Broker not connected")

        # Generate broker order ID
        broker_order_id = f"PAPER_{uuid.uuid4().hex[:8].upper()}"
        order.broker_order_id = broker_order_id
        order.status = OrderStatus.PENDING

        # Store order
        self._orders[order.order_id] = order

        # Log order placement
        self.logger.info(
            f"Order placed: {order.order_id} - "
            f"{order.transaction_type} {order.quantity} {order.instrument_id} "
            f"@ {order.price if order.price else 'MARKET'}"
        )

        # Notify order update
        self._notify_order_update(order)

        return broker_order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id not in self._orders:
            return False

        order = self._orders[order_id]
        if order.status in [
            OrderStatus.COMPLETE,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        ]:
            return False

        order.status = OrderStatus.CANCELLED
        self._notify_order_update(order)

        self.logger.info(f"Order cancelled: {order_id}")
        return True

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
    ) -> bool:
        """Modify an existing order."""
        if order_id not in self._orders:
            return False

        order = self._orders[order_id]
        if order.status != OrderStatus.OPEN:
            return False

        if quantity is not None:
            order.quantity = quantity
        if price is not None:
            order.price = price

        self._notify_order_update(order)
        self.logger.info(f"Order modified: {order_id}")
        return True

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get current status of an order."""
        return self._orders.get(order_id)

    async def get_orders(self) -> List[Order]:
        """Get all orders."""
        return list(self._orders.values())

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        return list(self._positions.values())

    async def get_position(self, instrument_id: str) -> Optional[Position]:
        """Get position for a specific instrument."""
        return self._positions.get(instrument_id)

    async def get_trades(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """Get trade history."""
        trades = self._trades.copy()

        if start_date:
            trades = [t for t in trades if t.timestamp >= start_date]
        if end_date:
            trades = [t for t in trades if t.timestamp <= end_date]

        return trades

    async def get_quote(self, instrument_id: str) -> Dict[str, Any]:
        """Get current quote for an instrument."""
        # Simulate market data
        if instrument_id not in self._market_prices:
            self._market_prices[instrument_id] = self._generate_initial_price(
                instrument_id
            )

        price = self._market_prices[instrument_id]
        spread = price * 0.001  # 0.1% spread

        return {
            "instrument_id": instrument_id,
            "bid": price - spread / 2,
            "ask": price + spread / 2,
            "last_price": price,
            "volume": random.randint(1000, 10000),
            "timestamp": datetime.now().isoformat(),
        }

    async def subscribe_quotes(
        self, instrument_ids: List[str], callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Subscribe to real-time quotes."""
        # Store callback for market updates
        for instrument_id in instrument_ids:
            if instrument_id not in self._market_prices:
                self._market_prices[instrument_id] = self._generate_initial_price(
                    instrument_id
                )

        self.logger.info(f"Subscribed to quotes for {len(instrument_ids)} instruments")

    async def unsubscribe_quotes(self, instrument_ids: List[str]) -> None:
        """Unsubscribe from real-time quotes."""
        self.logger.info(
            f"Unsubscribed from quotes for {len(instrument_ids)} instruments"
        )

    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance and margins."""
        # Calculate unrealized P&L
        unrealized_pnl = 0.0
        for position in self._positions.values():
            current_price = self._market_prices.get(
                position.instrument_id, position.last_price
            )
            unrealized_pnl += (
                current_price - position.average_price
            ) * position.quantity

        available_balance = self._account_balance - self._used_margin

        return {
            "cash": self._account_balance,
            "available_balance": available_balance,
            "used_margin": self._used_margin,
            "realized_pnl": self._realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_balance": self._account_balance
            + self._realized_pnl
            + unrealized_pnl,
        }

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get account holdings."""
        holdings = []
        for position in self._positions.values():
            current_price = self._market_prices.get(
                position.instrument_id, position.last_price
            )
            pnl = (current_price - position.average_price) * position.quantity

            holdings.append(
                {
                    "instrument_id": position.instrument_id,
                    "quantity": position.quantity,
                    "average_price": position.average_price,
                    "current_price": current_price,
                    "pnl": pnl,
                    "pnl_percentage": (
                        pnl / (position.average_price * abs(position.quantity))
                    )
                    * 100,
                }
            )

        return holdings

    # Private methods for simulation

    def _generate_initial_price(self, instrument_id: str) -> float:
        """Generate initial price for an instrument."""
        # Simple price generation based on instrument type
        if "NIFTY" in instrument_id.upper():
            return random.uniform(22000, 24000)
        elif "BANKNIFTY" in instrument_id.upper():
            return random.uniform(45000, 50000)
        elif ".OPT." in instrument_id:
            return random.uniform(50, 500)
        else:
            return random.uniform(100, 2000)

    async def _market_update_loop(self):
        """Background task to update market prices."""
        while self._connected:
            try:
                for instrument_id in self._market_prices:
                    # Simulate price movement
                    current_price = self._market_prices[instrument_id]
                    volatility = self._volatility.get(
                        instrument_id, 0.02
                    )  # 2% default volatility

                    # Random walk with drift
                    change_pct = random.gauss(0, volatility / 100)
                    new_price = current_price * (1 + change_pct)

                    # Ensure positive prices
                    new_price = max(new_price, 0.01)

                    self._market_prices[instrument_id] = new_price

                    # Store price history
                    if instrument_id not in self._price_history:
                        self._price_history[instrument_id] = []
                    self._price_history[instrument_id].append(new_price)

                    # Keep only last 100 prices
                    if len(self._price_history[instrument_id]) > 100:
                        self._price_history[instrument_id] = self._price_history[
                            instrument_id
                        ][-100:]

                await asyncio.sleep(1)  # Update every second

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in market update loop: {e}")
                await asyncio.sleep(1)

    async def _order_processing_loop(self):
        """Background task to process pending orders."""
        while self._connected:
            try:
                pending_orders = [
                    o for o in self._orders.values() if o.status == OrderStatus.PENDING
                ]

                for order in pending_orders:
                    await self._process_order(order)

                await asyncio.sleep(0.1)  # Check every 100ms

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in order processing loop: {e}")
                await asyncio.sleep(1)

    async def _process_order(self, order: Order):
        """Process a pending order."""
        # Simulate execution delay
        delay = random.uniform(*self._execution_delay_range)
        await asyncio.sleep(delay)

        # Check if order should be filled
        if random.random() > self._fill_probability:
            order.status = OrderStatus.REJECTED
            self._notify_order_update(order)
            return

        # Get current market price
        if order.instrument_id not in self._market_prices:
            self._market_prices[order.instrument_id] = self._generate_initial_price(
                order.instrument_id
            )

        market_price = self._market_prices[order.instrument_id]

        # Determine execution price
        if order.order_type == OrderType.MARKET:
            # Market orders execute at market price with slippage
            slippage = random.uniform(*self._slippage_range) / 100
            if order.transaction_type == TransactionType.BUY:
                execution_price = market_price * (1 + slippage)
            else:
                execution_price = market_price * (1 - slippage)
        else:
            # Limit orders execute at limit price if market allows
            if order.price is None:
                order.status = OrderStatus.REJECTED
                self._notify_order_update(order)
                return

            if (
                order.transaction_type == TransactionType.BUY
                and market_price <= order.price
            ):
                execution_price = order.price
            elif (
                order.transaction_type == TransactionType.SELL
                and market_price >= order.price
            ):
                execution_price = order.price
            else:
                # Order not filled yet
                order.status = OrderStatus.OPEN
                self._notify_order_update(order)
                return

        # Execute the order
        await self._execute_order(order, execution_price)

    async def _execute_order(self, order: Order, execution_price: float):
        """Execute an order at the given price."""
        # Calculate commission
        commission = self._calculate_commission(order, execution_price)

        # Create trade
        trade = Trade(
            trade_id=f"TRADE_{uuid.uuid4().hex[:8].upper()}",
            order_id=order.order_id,
            instrument_id=order.instrument_id,
            quantity=order.quantity,
            price=execution_price,
            transaction_type=order.transaction_type,
            timestamp=datetime.now(),
            commission=commission,
        )

        # Update order
        order.status = OrderStatus.COMPLETE
        order.filled_quantity = order.quantity
        order.average_price = execution_price

        # Update position
        await self._update_position(trade)

        # Update account balance
        trade_value = execution_price * order.quantity
        if order.transaction_type == TransactionType.BUY:
            self._account_balance -= trade_value + commission
        else:
            self._account_balance += trade_value - commission

        # Notify updates
        self._notify_order_update(order)
        self._notify_trade(trade)

        self.logger.info(
            f"Order executed: {order.order_id} - "
            f"{order.quantity} @ ₹{execution_price:.2f} "
            f"(Commission: ₹{commission:.2f})"
        )

    async def _update_position(self, trade: Trade):
        """Update position based on trade."""
        instrument_id = trade.instrument_id

        if instrument_id not in self._positions:
            # New position
            position = Position(
                instrument_id=instrument_id,
                quantity=trade.quantity
                if trade.transaction_type == TransactionType.BUY
                else -trade.quantity,
                average_price=trade.price,
                last_price=trade.price,
                pnl=0.0,
                unrealized_pnl=0.0,
                timestamp=trade.timestamp,
            )
        else:
            # Update existing position
            position = self._positions[instrument_id]

            if trade.transaction_type == TransactionType.BUY:
                new_quantity = position.quantity + trade.quantity
                if position.quantity >= 0:  # Adding to long position
                    total_cost = (position.average_price * position.quantity) + (
                        trade.price * trade.quantity
                    )
                    position.average_price = total_cost / new_quantity
                else:  # Covering short position
                    if new_quantity >= 0:
                        position.average_price = trade.price
                position.quantity = new_quantity
            else:  # SELL
                new_quantity = position.quantity - trade.quantity
                if position.quantity <= 0:  # Adding to short position
                    total_cost = abs(position.average_price * position.quantity) + (
                        trade.price * trade.quantity
                    )
                    position.average_price = total_cost / abs(new_quantity)
                else:  # Selling long position
                    if new_quantity <= 0:
                        position.average_price = trade.price
                position.quantity = new_quantity

            position.last_price = trade.price
            position.timestamp = trade.timestamp

        # Remove position if quantity is zero
        if position.quantity == 0:
            if instrument_id in self._positions:
                del self._positions[instrument_id]
        else:
            self._positions[instrument_id] = position
            self._notify_position_update(position)

    def _calculate_commission(self, order: Order, price: float) -> float:
        """Calculate commission for an order."""
        trade_value = price * order.quantity

        # Brokerage (flat per order)
        brokerage = self._brokerage_per_order

        # STT (only on sell side for equity, both sides for F&O)
        stt = 0.0
        if (
            order.transaction_type == TransactionType.SELL
            or ".OPT." in order.instrument_id
            or ".FUT." in order.instrument_id
        ):
            stt = trade_value * self._stt_rate

        # Transaction charges
        transaction_charges = trade_value * self._transaction_charges

        # GST on brokerage and transaction charges
        gst_rate = 0.18
        gst = (brokerage + transaction_charges) * gst_rate

        total_commission = brokerage + stt + transaction_charges + gst
        return round(total_commission, 2)
