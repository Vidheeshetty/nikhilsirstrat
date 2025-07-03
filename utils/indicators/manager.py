"""Indicator manager for coordinating multiple indicators.

This module provides a manager class that handles multiple indicators,
their lifecycle, and provides unified access to their outputs.
"""

from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

from .base import BaseIndicator, IndicatorConfig, IndicatorValue
from .registry import indicator_registry


class IndicatorManager:
    """Manager for coordinating multiple indicators."""
    
    def __init__(self):
        self._indicators: Dict[str, BaseIndicator] = {}
        self._enabled_indicators: Dict[str, BaseIndicator] = {}
        
    def load_from_config(self, config_path: str) -> None:
        """Load indicators from configuration file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        indicators_config = config_data.get('indicators', {})
        for indicator_name, indicator_data in indicators_config.items():
            self.add_indicator_from_dict(indicator_name, indicator_data)
    
    def add_indicator_from_dict(self, name: str, config_dict: Dict[str, Any]) -> bool:
        """Add indicator from dictionary configuration.
        
        Args:
            name: Unique name for this indicator instance
            config_dict: Dictionary containing indicator configuration
            
        Returns:
            True if indicator added successfully, False otherwise
        """
        try:
            config = IndicatorConfig(
                name=name,
                indicator_type=config_dict['type'],
                enabled=config_dict.get('enabled', True),
                visible_on_chart=config_dict.get('visible_on_chart', True),
                parameters=config_dict.get('parameters', {}),
                chart_settings=config_dict.get('chart_settings', {})
            )
            
            return self.add_indicator(config)
            
        except Exception as e:
            print(f"Failed to add indicator {name}: {e}")
            return False
    
    def add_indicator(self, config: IndicatorConfig) -> bool:
        """Add an indicator to the manager.
        
        Args:
            config: Indicator configuration
            
        Returns:
            True if indicator added successfully, False otherwise
        """
        indicator = indicator_registry.create_indicator(config)
        if not indicator:
            return False
        
        self._indicators[config.name] = indicator
        
        # Add to enabled indicators if enabled
        if config.enabled:
            self._enabled_indicators[config.name] = indicator
            
        print(f"Added indicator: {config.name} ({config.indicator_type})")
        return True
    
    def remove_indicator(self, name: str) -> bool:
        """Remove an indicator from the manager.
        
        Args:
            name: Name of the indicator to remove
            
        Returns:
            True if indicator removed successfully, False otherwise
        """
        if name in self._indicators:
            del self._indicators[name]
            if name in self._enabled_indicators:
                del self._enabled_indicators[name]
            print(f"Removed indicator: {name}")
            return True
        return False
    
    def enable_indicator(self, name: str) -> bool:
        """Enable an indicator.
        
        Args:
            name: Name of the indicator to enable
            
        Returns:
            True if indicator enabled successfully, False otherwise
        """
        if name in self._indicators:
            indicator = self._indicators[name]
            indicator.enabled = True
            self._enabled_indicators[name] = indicator
            print(f"Enabled indicator: {name}")
            return True
        return False
    
    def disable_indicator(self, name: str) -> bool:
        """Disable an indicator.
        
        Args:
            name: Name of the indicator to disable
            
        Returns:
            True if indicator disabled successfully, False otherwise
        """
        if name in self._indicators:
            indicator = self._indicators[name]
            indicator.enabled = False
            if name in self._enabled_indicators:
                del self._enabled_indicators[name]
            print(f"Disabled indicator: {name}")
            return True
        return False
    
    def toggle_chart_visibility(self, name: str) -> bool:
        """Toggle chart visibility for an indicator.
        
        Args:
            name: Name of the indicator
            
        Returns:
            True if visibility toggled successfully, False otherwise
        """
        if name in self._indicators:
            indicator = self._indicators[name]
            indicator.visible_on_chart = not indicator.visible_on_chart
            print(f"Toggled chart visibility for {name}: {indicator.visible_on_chart}")
            return True
        return False
    
    def update_all(self, data: Dict[str, float]) -> Dict[str, IndicatorValue]:
        """Update all enabled indicators with new data.
        
        Args:
            data: Dictionary containing OHLCV data
            
        Returns:
            Dictionary mapping indicator names to their latest values
        """
        results = {}
        
        for name, indicator in self._enabled_indicators.items():
            try:
                result = indicator.update(data)
                if result:
                    results[name] = result
            except Exception as e:
                print(f"Error updating indicator {name}: {e}")
        
        return results
    
    def get_current_values(self) -> Dict[str, Optional[IndicatorValue]]:
        """Get current values for all indicators.
        
        Returns:
            Dictionary mapping indicator names to their current values
        """
        return {
            name: indicator.get_current_value()
            for name, indicator in self._indicators.items()
        }
    
    def get_chart_configs(self) -> List[Dict[str, Any]]:
        """Get chart configurations for all visible indicators.
        
        Returns:
            List of chart configuration dictionaries
        """
        configs = []
        for indicator in self._indicators.values():
            if indicator.visible_on_chart:
                configs.append(indicator.get_chart_config())
        return configs
    
    def get_indicator_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all indicators.
        
        Returns:
            Dictionary mapping indicator names to their status information
        """
        return {
            name: indicator.get_status()
            for name, indicator in self._indicators.items()
        }
    
    def get_warmup_requirements(self) -> Dict[str, int]:
        """Get warmup requirements for all indicators.
        
        Returns:
            Dictionary mapping indicator names to required warmup bars
        """
        return {
            name: indicator.get_required_warmup_bars()
            for name, indicator in self._indicators.items()
        }
    
    def get_max_warmup_requirement(self) -> int:
        """Get the maximum warmup requirement across all indicators.
        
        Returns:
            Maximum number of warmup bars required
        """
        if not self._indicators:
            return 0
        
        return max(
            indicator.get_required_warmup_bars()
            for indicator in self._indicators.values()
        )
    
    def are_all_ready(self) -> bool:
        """Check if all enabled indicators are ready.
        
        Returns:
            True if all enabled indicators are ready, False otherwise
        """
        return all(
            indicator.is_ready()
            for indicator in self._enabled_indicators.values()
        )
    
    def reset_all(self) -> None:
        """Reset all indicators."""
        for indicator in self._indicators.values():
            indicator.reset()
        print("Reset all indicators")
    
    def get_indicator(self, name: str) -> Optional[BaseIndicator]:
        """Get a specific indicator by name.
        
        Args:
            name: Name of the indicator
            
        Returns:
            Indicator instance if found, None otherwise
        """
        return self._indicators.get(name)
    
    def list_indicators(self) -> List[str]:
        """Get list of all indicator names.
        
        Returns:
            List of indicator names
        """
        return list(self._indicators.keys())
    
    def list_enabled_indicators(self) -> List[str]:
        """Get list of enabled indicator names.
        
        Returns:
            List of enabled indicator names
        """
        return list(self._enabled_indicators.keys())
    
    def export_config(self, config_path: str) -> None:
        """Export current indicator configuration to file.
        
        Args:
            config_path: Path to save configuration file
        """
        config_data = {
            'indicators': {}
        }
        
        for name, indicator in self._indicators.items():
            config_data['indicators'][name] = {
                'type': indicator.config.indicator_type,
                'enabled': indicator.enabled,
                'visible_on_chart': indicator.visible_on_chart,
                'parameters': indicator.parameters,
                'chart_settings': indicator.config.chart_settings
            }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
        
        print(f"Exported indicator configuration to: {config_path}") 