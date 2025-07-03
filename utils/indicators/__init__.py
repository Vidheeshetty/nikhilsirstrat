"""Pluggable indicator system for trading strategies.

This module provides a pluggable indicator architecture that allows:
- Configuration-driven indicator management
- Separation of indicator calculation from strategy logic
- Chart visualization integration
- Easy testing and reusability
"""

from .base import BaseIndicator, IndicatorConfig
from .registry import IndicatorRegistry
from .manager import IndicatorManager

__all__ = [
    "BaseIndicator",
    "IndicatorConfig", 
    "IndicatorRegistry",
    "IndicatorManager",
] 