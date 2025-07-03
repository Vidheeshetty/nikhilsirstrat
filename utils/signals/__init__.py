"""Pluggable signal generation system for trading strategies.

This module provides a pluggable signal generation architecture that allows:
- Separation of signal logic from strategy execution
- Configuration-driven signal management
- Combination of multiple indicators for signal generation
- Easy testing and reusability of signal strategies
"""

from .base import BaseSignalGenerator, SignalConfig, TradingSignal, SignalType
from .registry import SignalRegistry, signal_registry
from .manager import SignalManager

__all__ = [
    "BaseSignalGenerator",
    "SignalConfig", 
    "TradingSignal",
    "SignalType",
    "SignalRegistry",
    "signal_registry",
    "SignalManager",
] 