"""Base classes for pluggable indicator system.

This module provides the foundation for a pluggable indicator architecture that allows:
- Configuration-driven indicator management
- Separation of indicator calculation from strategy logic
- Chart visualization integration
- Easy testing and reusability
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from enum import Enum


class IndicatorType(Enum):
    """Types of indicators for categorization."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    SUPPORT_RESISTANCE = "support_resistance"
    CUSTOM = "custom"


@dataclass
class IndicatorConfig:
    """Configuration for an indicator instance."""
    name: str
    indicator_type: str
    enabled: bool = True
    visible_on_chart: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    chart_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default chart settings if not provided."""
        if not self.chart_settings:
            self.chart_settings = {
                "color": "#3366CC",
                "line_width": 2,
                "line_style": "solid",
                "overlay": True  # True for price overlay, False for separate pane
            }


@dataclass
class IndicatorValue:
    """Container for indicator output values."""
    timestamp: pd.Timestamp
    values: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_main_value(self) -> Optional[float]:
        """Get the primary indicator value."""
        if "value" in self.values:
            return self.values["value"]
        elif len(self.values) == 1:
            return next(iter(self.values.values()))
        return None


class BaseIndicator(ABC):
    """Base class for all indicators in the pluggable system."""
    
    def __init__(self, config: IndicatorConfig):
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.enabled = config.enabled
        self.visible_on_chart = config.visible_on_chart
        
        # Internal state
        self._initialized = False
        self._buffer_size = self.parameters.get("buffer_size", 1000)
        self._data_buffer: List[Dict[str, float]] = []
        self._output_buffer: List[IndicatorValue] = []
        
        # Validation
        self._validate_parameters()
        
    @abstractmethod
    def _validate_parameters(self) -> None:
        """Validate indicator-specific parameters."""
        pass
    
    @abstractmethod
    def get_required_warmup_bars(self) -> int:
        """Return the number of historical bars needed for accurate calculation."""
        pass
    
    @abstractmethod
    def _calculate(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate indicator values from input data.
        
        Args:
            data: Dictionary containing OHLCV data
                 Keys: 'open', 'high', 'low', 'close', 'volume'
        
        Returns:
            Dictionary of calculated values
        """
        pass
    
    def update(self, data: Dict[str, float]) -> Optional[IndicatorValue]:
        """Update indicator with new bar data.
        
        Args:
            data: Dictionary containing OHLCV data with 'timestamp'
            
        Returns:
            IndicatorValue if calculation successful, None otherwise
        """
        if not self.enabled:
            return None
            
        # Add to buffer
        self._data_buffer.append(data.copy())
        if len(self._data_buffer) > self._buffer_size:
            self._data_buffer.pop(0)
            
        # Calculate if we have enough data
        if len(self._data_buffer) >= self.get_required_warmup_bars():
            try:
                calculated_values = self._calculate(data)
                
                indicator_value = IndicatorValue(
                    timestamp=data.get('timestamp', pd.Timestamp.now()),
                    values=calculated_values,
                    metadata={
                        'indicator_name': self.name,
                        'indicator_type': self.config.indicator_type,
                        'buffer_size': len(self._data_buffer)
                    }
                )
                
                # Add to output buffer
                self._output_buffer.append(indicator_value)
                if len(self._output_buffer) > self._buffer_size:
                    self._output_buffer.pop(0)
                    
                self._initialized = True
                return indicator_value
                
            except Exception as e:
                print(f"Error calculating {self.name}: {e}")
                return None
        
        return None
    
    def get_current_value(self) -> Optional[IndicatorValue]:
        """Get the most recent indicator value."""
        if self._output_buffer:
            return self._output_buffer[-1]
        return None
    
    def get_historical_values(self, lookback: int = 50) -> List[IndicatorValue]:
        """Get historical indicator values."""
        return self._output_buffer[-lookback:] if self._output_buffer else []
    
    def is_ready(self) -> bool:
        """Check if indicator has enough data for reliable calculations."""
        return self._initialized and len(self._data_buffer) >= self.get_required_warmup_bars()
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart visualization configuration."""
        return {
            "name": self.name,
            "type": self.config.indicator_type,
            "visible": self.visible_on_chart,
            "settings": self.config.chart_settings,
            "overlay": self.config.chart_settings.get("overlay", True)
        }
    
    def reset(self) -> None:
        """Reset indicator state."""
        self._data_buffer.clear()
        self._output_buffer.clear()
        self._initialized = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get indicator status information."""
        return {
            "name": self.name,
            "type": self.config.indicator_type,
            "enabled": self.enabled,
            "ready": self.is_ready(),
            "buffer_size": len(self._data_buffer),
            "warmup_required": self.get_required_warmup_bars(),
            "current_value": self.get_current_value().get_main_value() if self.get_current_value() else None
        } 