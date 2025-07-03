"""Concrete implementations of common trading indicators.

This module provides implementations of popular technical indicators
using the pluggable indicator architecture.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from collections import deque

from .base import BaseIndicator, IndicatorConfig


class SMAIndicator(BaseIndicator):
    """Simple Moving Average indicator."""
    
    def _validate_parameters(self) -> None:
        """Validate SMA parameters."""
        if "period" not in self.parameters:
            raise ValueError("SMA requires 'period' parameter")
        
        period = self.parameters["period"]
        if not isinstance(period, int) or period <= 0:
            raise ValueError("SMA period must be a positive integer")
    
    def get_required_warmup_bars(self) -> int:
        """Return required warmup bars for SMA."""
        return self.parameters["period"]
    
    def _calculate(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate SMA value."""
        period = self.parameters["period"]
        
        # Get the last 'period' close prices
        close_prices = [bar["close"] for bar in self._data_buffer[-period:]]
        sma_value = sum(close_prices) / len(close_prices)
        
        return {"value": sma_value}


class EMAIndicator(BaseIndicator):
    """Exponential Moving Average indicator."""
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config)
        self._ema_value = None
        self._alpha = 2.0 / (self.parameters["period"] + 1)
    
    def _validate_parameters(self) -> None:
        """Validate EMA parameters."""
        if "period" not in self.parameters:
            raise ValueError("EMA requires 'period' parameter")
        
        period = self.parameters["period"]
        if not isinstance(period, int) or period <= 0:
            raise ValueError("EMA period must be a positive integer")
    
    def get_required_warmup_bars(self) -> int:
        """Return required warmup bars for EMA."""
        return 1  # EMA can start with first bar
    
    def _calculate(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate EMA value."""
        close_price = data["close"]
        
        if self._ema_value is None:
            # Initialize with first close price
            self._ema_value = close_price
        else:
            # Calculate EMA: EMA = (Close * Alpha) + (Previous EMA * (1 - Alpha))
            self._ema_value = (close_price * self._alpha) + (self._ema_value * (1 - self._alpha))
        
        return {"value": self._ema_value}


class RSIIndicator(BaseIndicator):
    """Relative Strength Index indicator."""
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config)
        self._gains = deque(maxlen=self.parameters["period"])
        self._losses = deque(maxlen=self.parameters["period"])
        self._prev_close = None
    
    def _validate_parameters(self) -> None:
        """Validate RSI parameters."""
        if "period" not in self.parameters:
            raise ValueError("RSI requires 'period' parameter")
        
        period = self.parameters["period"]
        if not isinstance(period, int) or period <= 0:
            raise ValueError("RSI period must be a positive integer")
    
    def get_required_warmup_bars(self) -> int:
        """Return required warmup bars for RSI."""
        return self.parameters["period"] + 1  # Need one extra for price change calculation
    
    def _calculate(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate RSI value."""
        close_price = data["close"]
        
        if self._prev_close is not None:
            # Calculate price change
            change = close_price - self._prev_close
            
            # Separate gains and losses
            gain = max(change, 0)
            loss = max(-change, 0)
            
            self._gains.append(gain)
            self._losses.append(loss)
            
            # Calculate RSI when we have enough data
            if len(self._gains) >= self.parameters["period"]:
                avg_gain = sum(self._gains) / len(self._gains)
                avg_loss = sum(self._losses) / len(self._losses)
                
                if avg_loss == 0:
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100.0 - (100.0 / (1.0 + rs))
                
                self._prev_close = close_price
                return {"value": rsi}
        
        self._prev_close = close_price
        return {"value": 50.0}  # Neutral RSI while warming up


class FractalIndicator(BaseIndicator):
    """Fractal indicator for identifying swing highs and lows."""
    
    def _validate_parameters(self) -> None:
        """Validate Fractal parameters."""
        if "window" not in self.parameters:
            self.parameters["window"] = 5  # Default window
        
        window = self.parameters["window"]
        if not isinstance(window, int) or window < 3 or window % 2 == 0:
            raise ValueError("Fractal window must be an odd integer >= 3")
    
    def get_required_warmup_bars(self) -> int:
        """Return required warmup bars for Fractal."""
        return self.parameters["window"]
    
    def _calculate(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate Fractal values."""
        window = self.parameters["window"]
        half_window = window // 2
        
        if len(self._data_buffer) < window:
            return {"fractal_high": 0, "fractal_low": 0}
        
        # Get the middle bar (the one we're checking for fractal)
        middle_idx = len(self._data_buffer) - half_window - 1
        middle_bar = self._data_buffer[middle_idx]
        
        # Check for fractal high
        is_fractal_high = True
        for i in range(middle_idx - half_window, middle_idx + half_window + 1):
            if i != middle_idx and self._data_buffer[i]["high"] >= middle_bar["high"]:
                is_fractal_high = False
                break
        
        # Check for fractal low
        is_fractal_low = True
        for i in range(middle_idx - half_window, middle_idx + half_window + 1):
            if i != middle_idx and self._data_buffer[i]["low"] <= middle_bar["low"]:
                is_fractal_low = False
                break
        
        return {
            "fractal_high": middle_bar["high"] if is_fractal_high else 0,
            "fractal_low": middle_bar["low"] if is_fractal_low else 0
        }


class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands indicator."""
    
    def _validate_parameters(self) -> None:
        """Validate Bollinger Bands parameters."""
        if "period" not in self.parameters:
            self.parameters["period"] = 20  # Default period
        if "std_dev" not in self.parameters:
            self.parameters["std_dev"] = 2.0  # Default standard deviation multiplier
        
        period = self.parameters["period"]
        if not isinstance(period, int) or period <= 0:
            raise ValueError("Bollinger Bands period must be a positive integer")
        
        std_dev = self.parameters["std_dev"]
        if not isinstance(std_dev, (int, float)) or std_dev <= 0:
            raise ValueError("Bollinger Bands std_dev must be a positive number")
    
    def get_required_warmup_bars(self) -> int:
        """Return required warmup bars for Bollinger Bands."""
        return self.parameters["period"]
    
    def _calculate(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate Bollinger Bands values."""
        period = self.parameters["period"]
        std_dev_multiplier = self.parameters["std_dev"]
        
        # Get the last 'period' close prices
        close_prices = [bar["close"] for bar in self._data_buffer[-period:]]
        
        # Calculate middle band (SMA)
        middle_band = sum(close_prices) / len(close_prices)
        
        # Calculate standard deviation
        variance = sum((price - middle_band) ** 2 for price in close_prices) / len(close_prices)
        std_dev = variance ** 0.5
        
        # Calculate upper and lower bands
        upper_band = middle_band + (std_dev_multiplier * std_dev)
        lower_band = middle_band - (std_dev_multiplier * std_dev)
        
        return {
            "upper_band": upper_band,
            "middle_band": middle_band,
            "lower_band": lower_band
        } 