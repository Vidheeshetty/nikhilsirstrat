"""Signal registry for managing pluggable signal generators.

This module provides a registry system for signal generator discovery, 
registration, and instantiation based on configuration.
"""

from typing import Dict, Type, List, Optional, Any
import importlib
import inspect
from pathlib import Path

from .base import BaseSignalGenerator, SignalConfig


class SignalRegistry:
    """Registry for managing pluggable signal generators."""
    
    def __init__(self):
        self._signal_generators: Dict[str, Type[BaseSignalGenerator]] = {}
        self._load_builtin_signal_generators()
    
    def register(self, name: str, signal_generator_class: Type[BaseSignalGenerator]) -> None:
        """Register a signal generator class.
        
        Args:
            name: Unique name for the signal generator
            signal_generator_class: Class implementing BaseSignalGenerator
        """
        if not issubclass(signal_generator_class, BaseSignalGenerator):
            raise ValueError(f"Signal generator class {signal_generator_class} must inherit from BaseSignalGenerator")
        
        self._signal_generators[name] = signal_generator_class
        print(f"Registered signal generator: {name}")
    
    def get_signal_generator_class(self, name: str) -> Optional[Type[BaseSignalGenerator]]:
        """Get signal generator class by name.
        
        Args:
            name: Name of the signal generator
            
        Returns:
            Signal generator class if found, None otherwise
        """
        return self._signal_generators.get(name)
    
    def create_signal_generator(self, config: SignalConfig) -> Optional[BaseSignalGenerator]:
        """Create a signal generator instance from configuration.
        
        Args:
            config: Signal generator configuration
            
        Returns:
            Signal generator instance if successful, None otherwise
        """
        signal_generator_class = self.get_signal_generator_class(config.signal_type)
        if not signal_generator_class:
            print(f"Unknown signal generator type: {config.signal_type}")
            return None
        
        try:
            return signal_generator_class(config)
        except Exception as e:
            print(f"Failed to create signal generator {config.name}: {e}")
            return None
    
    def list_signal_generators(self) -> List[str]:
        """Get list of registered signal generator names."""
        return list(self._signal_generators.keys())
    
    def get_signal_generator_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered signal generator.
        
        Args:
            name: Name of the signal generator
            
        Returns:
            Dictionary with signal generator information
        """
        signal_generator_class = self.get_signal_generator_class(name)
        if not signal_generator_class:
            return None
        
        return {
            "name": name,
            "class": signal_generator_class.__name__,
            "module": signal_generator_class.__module__,
            "docstring": signal_generator_class.__doc__ or "No description available",
            "required_parameters": self._get_required_parameters(signal_generator_class)
        }
    
    def _get_required_parameters(self, signal_generator_class: Type[BaseSignalGenerator]) -> List[str]:
        """Extract required parameters from signal generator class."""
        try:
            signature = inspect.signature(signal_generator_class.__init__)
            return [param.name for param in signature.parameters.values() 
                   if param.name != 'self' and param.name != 'config']
        except Exception:
            return []
    
    def _load_builtin_signal_generators(self) -> None:
        """Load built-in signal generators from the implementations module."""
        try:
            # Import built-in signal generators
            from .implementations import (
                SMAFractalSignalGenerator,
                RSIBollingerSignalGenerator,
                TrendFollowingSignalGenerator,
                MeanReversionSignalGenerator
            )
            
            # Register built-in signal generators
            self.register("sma_fractal", SMAFractalSignalGenerator)
            self.register("rsi_bollinger", RSIBollingerSignalGenerator)
            self.register("trend_following", TrendFollowingSignalGenerator)
            self.register("mean_reversion", MeanReversionSignalGenerator)
            
        except ImportError as e:
            print(f"Warning: Could not load built-in signal generators: {e}")
    
    def load_custom_signal_generators(self, signals_path: str) -> None:
        """Load custom signal generators from a directory.
        
        Args:
            signals_path: Path to directory containing custom signal generators
        """
        signals_dir = Path(signals_path)
        if not signals_dir.exists():
            print(f"Custom signals directory not found: {signals_path}")
            return
        
        # Look for Python files in the directory
        for py_file in signals_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                # Import the module
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find signal generator classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseSignalGenerator) and 
                        obj != BaseSignalGenerator and 
                        obj.__module__ == module_name):
                        
                        signal_name = name.lower().replace("signalgenerator", "")
                        self.register(signal_name, obj)
                        
            except Exception as e:
                print(f"Failed to load custom signal generator from {py_file}: {e}")


# Global registry instance
signal_registry = SignalRegistry()