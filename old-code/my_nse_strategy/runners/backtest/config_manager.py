#!/usr/bin/env python3
"""
Configuration Manager for MyNSEStrategy Backtesting

Handles loading, validation, and management of backtest configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.currencies import INR
from strategies.my_nse_strategy.config import MyNSEStrategyConfig


class ConfigManager:
    """Manages backtest configuration loading and validation."""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    def get_strategy_config(self, instrument_id: str) -> MyNSEStrategyConfig:
        """Get strategy configuration with instrument ID override."""
        config = self.config.copy()
        if instrument_id is None:
            instrument_id = config.get("instrument_id")
        config["instrument_id"] = InstrumentId.from_str(instrument_id)
        
        # Remove backtest-specific parameters that are not part of strategy config
        backtest_params = ["start_time", "end_time"]
        for param in backtest_params:
            config.pop(param, None)
        
        return MyNSEStrategyConfig(**config)
    
    def get_backtest_params(self, 
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None) -> Dict[str, Any]:
        """Get backtest parameters with optional overrides."""
        params = {
            "start_time": start_time or self.config.get("start_time"),
            "end_time": end_time or self.config.get("end_time"),
            "base_currency": INR,
        }
        return params
    
    def validate_config(self) -> bool:
        """Validate configuration parameters."""
        required_fields = ["instrument_id", "start_time", "end_time"]
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required configuration field: {field}")
        return True 