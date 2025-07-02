"""
Broker Manager

Manages multiple broker connections and provides unified interface for trading.
Handles broker selection, failover, and load balancing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import yaml

from .base import BaseBroker, BrokerConfig, Order, Position
from .paper import PaperBroker
from .zerodha import ZerodhaBroker, ZerodhaConfig

logger = logging.getLogger(__name__)


class BrokerManager:
    """
    Manages multiple broker connections and provides unified trading interface.

    Features:
    - Multiple broker support
    - Automatic failover
    - Load balancing
    - Unified order routing
    - Health monitoring
    """

    def __init__(self):
        """Initialize broker manager."""
        self._brokers: Dict[str, BaseBroker] = {}
        self._broker_configs: Dict[str, BrokerConfig] = {}
        self._primary_broker: Optional[str] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_status: Dict[str, Dict[str, Any]] = {}

        # Broker class registry
        self._broker_classes: Dict[str, Type[BaseBroker]] = {
            "paper": PaperBroker,
            "zerodha": ZerodhaBroker,
        }

        self.logger = logging.getLogger(__name__)

    async def initialize(self, config_file: str) -> None:
        """Initialize broker manager from configuration file."""
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)

            # Load broker configurations
            broker_configs = config.get("brokers", {})

            for broker_name, broker_config in broker_configs.items():
                await self.add_broker(broker_name, broker_config)

            # Set primary broker
            if broker_configs:
                self._primary_broker = list(broker_configs.keys())[0]

            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            self.logger.info(
                f"Broker manager initialized with {len(self._brokers)} brokers"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize broker manager: {e}")
            raise

    async def add_broker(self, name: str, config: Dict[str, Any]) -> None:
        """Add a broker to the manager."""
        try:
            broker_type = config.get("broker_name", name)

            # Create broker configuration
            if broker_type == "zerodha":
                broker_config = ZerodhaConfig(**config)
            else:
                broker_config = BrokerConfig(**config)

            # Create broker instance
            if broker_type in self._broker_classes:
                broker_class = self._broker_classes[broker_type]
                broker = broker_class(broker_config)
            else:
                # Default to paper broker for unknown types
                broker = PaperBroker(broker_config)

            # Connect to broker
            connected = await broker.connect()
            if not connected:
                raise RuntimeError(f"Failed to connect to {name} broker")

            self._brokers[name] = broker
            self._broker_configs[name] = broker_config

            self.logger.info(f"Added broker: {name} ({broker_type})")

        except Exception as e:
            self.logger.error(f"Failed to add broker {name}: {e}")
            raise

    async def remove_broker(self, name: str) -> None:
        """Remove a broker from the manager."""
        if name in self._brokers:
            broker = self._brokers[name]
            await broker.disconnect()
            del self._brokers[name]
            del self._broker_configs[name]

            if self._primary_broker == name:
                # Set new primary broker
                if self._brokers:
                    self._primary_broker = list(self._brokers.keys())[0]
                else:
                    self._primary_broker = None

            self.logger.info(f"Removed broker: {name}")

    async def shutdown(self) -> None:
        """Shutdown broker manager and disconnect all brokers."""
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()

        # Disconnect all brokers
        for name, broker in self._brokers.items():
            try:
                await broker.disconnect()
                self.logger.info(f"Disconnected broker: {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting broker {name}: {e}")

        self._brokers.clear()
        self._broker_configs.clear()
        self._primary_broker = None

        self.logger.info("Broker manager shutdown complete")

    # Broker Selection and Routing

    def get_broker(self, name: Optional[str] = None) -> Optional[BaseBroker]:
        """Get a broker by name or return primary broker."""
        if name:
            return self._brokers.get(name)
        elif self._primary_broker:
            return self._brokers.get(self._primary_broker)
        else:
            return None

    def get_available_brokers(self) -> List[str]:
        """Get list of available broker names."""
        return [name for name, broker in self._brokers.items() if broker.is_connected]

    def get_healthy_brokers(self) -> List[str]:
        """Get list of healthy broker names."""
        healthy = []
        for name, status in self._health_status.items():
            if status.get("status") == "healthy":
                healthy.append(name)
        return healthy

    def select_best_broker(self, criteria: str = "health") -> Optional[str]:
        """Select the best broker based on criteria."""
        if criteria == "health":
            healthy_brokers = self.get_healthy_brokers()
            return healthy_brokers[0] if healthy_brokers else None
        elif criteria == "primary":
            return (
                self._primary_broker if self._primary_broker in self._brokers else None
            )
        else:
            available = self.get_available_brokers()
            return available[0] if available else None

    # Order Management (Unified Interface)

    async def place_order(self, order: Order, broker_name: Optional[str] = None) -> str:
        """Place an order through specified or best available broker."""
        broker_name = broker_name or self.select_best_broker()
        if not broker_name:
            raise RuntimeError("No available brokers")

        broker = self.get_broker(broker_name)
        if not broker:
            raise RuntimeError(f"Broker {broker_name} not found")

        try:
            result = await broker.place_order(order)
            self.logger.info(f"Order placed via {broker_name}: {order.order_id}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to place order via {broker_name}: {e}")

            # Try failover to another broker
            alternative_brokers = [
                b for b in self.get_healthy_brokers() if b != broker_name
            ]
            if alternative_brokers:
                self.logger.info(f"Attempting failover to {alternative_brokers[0]}")
                return await self.place_order(order, alternative_brokers[0])
            else:
                raise

    async def cancel_order(
        self, order_id: str, broker_name: Optional[str] = None
    ) -> bool:
        """Cancel an order through specified or primary broker."""
        broker_name = broker_name or self._primary_broker
        if not broker_name:
            return False

        broker = self.get_broker(broker_name)
        if not broker:
            return False

        return await broker.cancel_order(order_id)

    async def get_orders(self, broker_name: Optional[str] = None) -> List[Order]:
        """Get orders from specified or all brokers."""
        if broker_name:
            broker = self.get_broker(broker_name)
            return await broker.get_orders() if broker else []
        else:
            # Aggregate orders from all brokers
            all_orders = []
            for broker in self._brokers.values():
                try:
                    orders = await broker.get_orders()
                    all_orders.extend(orders)
                except Exception as e:
                    self.logger.error(
                        f"Error getting orders from {broker.broker_name}: {e}"
                    )
            return all_orders

    # Position Management

    async def get_positions(self, broker_name: Optional[str] = None) -> List[Position]:
        """Get positions from specified or all brokers."""
        if broker_name:
            broker = self.get_broker(broker_name)
            return await broker.get_positions() if broker else []
        else:
            # Aggregate positions from all brokers
            all_positions = []
            for broker in self._brokers.values():
                try:
                    positions = await broker.get_positions()
                    all_positions.extend(positions)
                except Exception as e:
                    self.logger.error(
                        f"Error getting positions from {broker.broker_name}: {e}"
                    )
            return all_positions

    # Account Information

    async def get_account_balance(
        self, broker_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get account balance from specified or all brokers."""
        if broker_name:
            broker = self.get_broker(broker_name)
            return await broker.get_account_balance() if broker else {}
        else:
            # Aggregate balances from all brokers
            balances = {}
            for name, broker in self._brokers.items():
                try:
                    balance = await broker.get_account_balance()
                    balances[name] = balance
                except Exception as e:
                    self.logger.error(f"Error getting balance from {name}: {e}")
                    balances[name] = {"error": str(e)}
            return balances

    # Market Data

    async def get_quote(
        self, instrument_id: str, broker_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get quote from specified or best available broker."""
        broker_name = broker_name or self.select_best_broker()
        if not broker_name:
            raise RuntimeError("No available brokers")

        broker = self.get_broker(broker_name)
        if not broker:
            raise RuntimeError(f"Broker {broker_name} not found")

        return await broker.get_quote(instrument_id)

    # Health Monitoring

    async def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all brokers."""
        return self._health_status.copy()

    async def _health_check_loop(self):
        """Background task to monitor broker health."""
        while True:
            try:
                for name, broker in self._brokers.items():
                    try:
                        health = await broker.health_check()
                        self._health_status[name] = health
                    except Exception as e:
                        self._health_status[name] = {
                            "status": "unhealthy",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                        }

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)

    # Statistics and Reporting

    def get_statistics(self) -> Dict[str, Any]:
        """Get broker manager statistics."""
        return {
            "total_brokers": len(self._brokers),
            "connected_brokers": len(self.get_available_brokers()),
            "healthy_brokers": len(self.get_healthy_brokers()),
            "primary_broker": self._primary_broker,
            "broker_types": {
                name: config.broker_name
                for name, config in self._broker_configs.items()
            },
        }
