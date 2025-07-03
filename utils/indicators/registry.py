"""Indicator registry for managing pluggable indicators.

This module provides a registry system for indicator discovery, registration,
and instantiation based on configuration.
"""

from typing import Dict, Type, List, Optional, Any
import importlib
import inspect
from pathlib import Path

from .base import BaseIndicator, IndicatorConfig


class IndicatorRegistry:
    """Registry for managing pluggable indicators."""
    
    def __init__(self):
        self._indicators: Dict[str, Type[BaseIndicator]] = {}
        self._load_builtin_indicators()
    
    def register(self, name: str, indicator_class: Type[BaseIndicator]) -> None:
        """Register an indicator class.
        
        Args:
            name: Unique name for the indicator
            indicator_class: Class implementing BaseIndicator
        """
        if not issubclass(indicator_class, BaseIndicator):
            raise ValueError(f"Indicator class {indicator_class} must inherit from BaseIndicator")
        
        self._indicators[name] = indicator_class
        print(f"Registered indicator: {name}")
    
    def get_indicator_class(self, name: str) -> Optional[Type[BaseIndicator]]:
        """Get indicator class by name.
        
        Args:
            name: Name of the indicator
            
        Returns:
            Indicator class if found, None otherwise
        """
        return self._indicators.get(name)
    
    def create_indicator(self, config: IndicatorConfig) -> Optional[BaseIndicator]:
        """Create an indicator instance from configuration.
        
        Args:
            config: Indicator configuration
            
        Returns:
            Indicator instance if successful, None otherwise
        """
        indicator_class = self.get_indicator_class(config.indicator_type)
        if not indicator_class:
            print(f"Unknown indicator type: {config.indicator_type}")
            return None
        
        try:
            return indicator_class(config)
        except Exception as e:
            print(f"Failed to create indicator {config.name}: {e}")
            return None
    
    def list_indicators(self) -> List[str]:
        """Get list of registered indicator names."""
        return list(self._indicators.keys())
    
    def get_indicator_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered indicator.
        
        Args:
            name: Name of the indicator
            
        Returns:
            Dictionary with indicator information
        """
        indicator_class = self.get_indicator_class(name)
        if not indicator_class:
            return None
        
        return {
            "name": name,
            "class": indicator_class.__name__,
            "module": indicator_class.__module__,
            "docstring": indicator_class.__doc__ or "No description available",
            "required_parameters": self._get_required_parameters(indicator_class)
        }
    
    def _get_required_parameters(self, indicator_class: Type[BaseIndicator]) -> List[str]:
        """Extract required parameters from indicator class."""
        # This is a simplified implementation
        # In practice, you might want to use annotations or docstrings
        try:
            signature = inspect.signature(indicator_class.__init__)
            return [param.name for param in signature.parameters.values() 
                   if param.name != 'self' and param.name != 'config']
        except Exception:
            return []
    
    def _load_builtin_indicators(self) -> None:
        """Load built-in indicators from the indicators package."""
        try:
            # Import built-in indicators
            from .implementations import (
                SMAIndicator,
                EMAIndicator, 
                RSIIndicator,
                FractalIndicator,
                BollingerBandsIndicator
            )
            
            # Register built-in indicators
            self.register("sma", SMAIndicator)
            self.register("ema", EMAIndicator)
            self.register("rsi", RSIIndicator)
            self.register("fractal", FractalIndicator)
            self.register("bollinger_bands", BollingerBandsIndicator)
            
        except ImportError as e:
            print(f"Warning: Could not load built-in indicators: {e}")
    
    def load_custom_indicators(self, indicators_path: str) -> None:
        """Load custom indicators from a directory.
        
        Args:
            indicators_path: Path to directory containing custom indicators
        """
        indicators_dir = Path(indicators_path)
        if not indicators_dir.exists():
            print(f"Custom indicators directory not found: {indicators_path}")
            return
        
        # Look for Python files in the directory
        for py_file in indicators_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                # Import the module
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find indicator classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseIndicator) and 
                        obj != BaseIndicator and 
                        obj.__module__ == module_name):
                        
                        indicator_name = name.lower().replace("indicator", "")
                        self.register(indicator_name, obj)
                        
            except Exception as e:
                print(f"Failed to load custom indicator from {py_file}: {e}")


# Global registry instance
indicator_registry = IndicatorRegistry() 