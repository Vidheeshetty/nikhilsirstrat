"""Base classes for pluggable signal generation system.

This module provides the foundation for signal generation that combines
indicator outputs to produce trading signals.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd

from utils.indicators.base import IndicatorValue


class SignalType(Enum):
    """Types of trading signals."""
    LONG = "long"
    SHORT = "short" 
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"
    NO_SIGNAL = "no_signal"


@dataclass
class TradingSignal:
    """Container for trading signal information."""
    signal_type: SignalType
    timestamp: pd.Timestamp
    confidence: float  # 0.0 to 1.0
    price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    
    def is_entry_signal(self) -> bool:
        """Check if this is an entry signal."""
        return self.signal_type in [SignalType.LONG, SignalType.SHORT]
    
    def is_exit_signal(self) -> bool:
        """Check if this is an exit signal."""
        return self.signal_type in [SignalType.EXIT_LONG, SignalType.EXIT_SHORT]
    
    def is_actionable(self) -> bool:
        """Check if this signal requires action."""
        return self.signal_type != SignalType.NO_SIGNAL and self.signal_type != SignalType.HOLD


@dataclass
class SignalConfig:
    """Configuration for a signal generator."""
    name: str
    signal_type: str
    enabled: bool = True
    required_indicators: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.5
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")


class BaseSignalGenerator(ABC):
    """Base class for all signal generators."""
    
    def __init__(self, config: SignalConfig):
        self.config = config
        self.name = config.name
        self.signal_type = config.signal_type
        self.enabled = config.enabled
        self.required_indicators = config.required_indicators
        self.parameters = config.parameters
        self.confidence_threshold = config.confidence_threshold
        
        # Internal state
        self._last_signal: Optional[TradingSignal] = None
        self._signal_history: List[TradingSignal] = []
        self._max_history = self.parameters.get("max_history", 100)
        
        # Validation
        self._validate_parameters()
    
    @abstractmethod
    def _validate_parameters(self) -> None:
        """Validate signal generator specific parameters."""
        pass
    
    @abstractmethod
    def _generate_signal(
        self, 
        indicator_values: Dict[str, IndicatorValue],
        market_data: Dict[str, float]
    ) -> TradingSignal:
        """Generate trading signal from indicator values and market data.
        
        Args:
            indicator_values: Dictionary mapping indicator names to their current values
            market_data: Dictionary containing current OHLCV data
            
        Returns:
            TradingSignal instance
        """
        pass
    
    def generate_signal(
        self,
        indicator_values: Dict[str, IndicatorValue], 
        market_data: Dict[str, float]
    ) -> Optional[TradingSignal]:
        """Generate trading signal with validation and filtering.
        
        Args:
            indicator_values: Dictionary mapping indicator names to their current values
            market_data: Dictionary containing current OHLCV data
            
        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        if not self.enabled:
            return None
        
        # Check if all required indicators are available
        missing_indicators = []
        for required_indicator in self.required_indicators:
            if required_indicator not in indicator_values:
                missing_indicators.append(required_indicator)
        
        if missing_indicators:
            return TradingSignal(
                signal_type=SignalType.NO_SIGNAL,
                timestamp=market_data.get('timestamp', pd.Timestamp.now()),
                confidence=0.0,
                reasons=[f"Missing indicators: {', '.join(missing_indicators)}"]
            )
        
        try:
            # Generate the signal
            signal = self._generate_signal(indicator_values, market_data)
            
            # Apply confidence threshold
            if signal.confidence < self.confidence_threshold:
                signal = TradingSignal(
                    signal_type=SignalType.NO_SIGNAL,
                    timestamp=signal.timestamp,
                    confidence=signal.confidence,
                    reasons=signal.reasons + [f"Confidence {signal.confidence:.2f} below threshold {self.confidence_threshold:.2f}"]
                )
            
            # Store signal
            self._last_signal = signal
            self._signal_history.append(signal)
            
            # Maintain history size
            if len(self._signal_history) > self._max_history:
                self._signal_history.pop(0)
            
            return signal
            
        except Exception as e:
            error_signal = TradingSignal(
                signal_type=SignalType.NO_SIGNAL,
                timestamp=market_data.get('timestamp', pd.Timestamp.now()),
                confidence=0.0,
                reasons=[f"Signal generation error: {str(e)}"]
            )
            self._last_signal = error_signal
            return error_signal
    
    def get_last_signal(self) -> Optional[TradingSignal]:
        """Get the most recent signal."""
        return self._last_signal
    
    def get_signal_history(self, lookback: int = 10) -> List[TradingSignal]:
        """Get recent signal history.
        
        Args:
            lookback: Number of recent signals to return
            
        Returns:
            List of recent signals
        """
        return self._signal_history[-lookback:] if self._signal_history else []
    
    def get_status(self) -> Dict[str, Any]:
        """Get signal generator status information.
        
        Returns:
            Dictionary containing status information
        """
        return {
            "name": self.name,
            "type": self.signal_type,
            "enabled": self.enabled,
            "required_indicators": self.required_indicators,
            "confidence_threshold": self.confidence_threshold,
            "last_signal": {
                "type": self._last_signal.signal_type.value if self._last_signal else None,
                "confidence": self._last_signal.confidence if self._last_signal else None,
                "timestamp": self._last_signal.timestamp.isoformat() if self._last_signal else None
            },
            "signal_count": len(self._signal_history)
        }
    
    def reset(self) -> None:
        """Reset signal generator state."""
        self._last_signal = None
        self._signal_history.clear()
    
    def can_generate_signal(self, available_indicators: List[str]) -> bool:
        """Check if signal can be generated with available indicators.
        
        Args:
            available_indicators: List of available indicator names
            
        Returns:
            True if all required indicators are available
        """
        return all(
            indicator in available_indicators 
            for indicator in self.required_indicators
        ) 