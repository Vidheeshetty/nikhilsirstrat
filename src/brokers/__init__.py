"""
Broker Integration Package

Multi-broker integration for paper trading and live trading.
Supports Zerodha, Upstox, Angel One, and other Indian brokers.

Package Structure:
    - base/: Base broker interface and common utilities
    - zerodha/: Zerodha KiteConnect integration
    - upstox/: Upstox API integration
    - angel_one/: Angel One SmartAPI integration
    - paper/: Paper trading simulator
    - manager/: Broker management and routing
"""

from .base import BaseBroker, BrokerConfig
from .manager import BrokerManager
from .paper import PaperBroker

__all__ = ["BaseBroker", "BrokerConfig", "BrokerManager", "PaperBroker"]

__version__ = "1.0.0"
