"""
Generic Configuration Loader for Backtesting

This module provides a generic configuration loader for backtesting strategies.
It handles loading and validating configuration from JSON files.
"""

import json
from typing import Dict, Any


class BacktestConfigLoader:
    """Generic configuration loader for backtesting."""

    def __init__(self, config_file: str):
        """
        Initialize the configuration loader.

        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = None

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the specified file.

        Returns:
            Dictionary containing configuration parameters

        Raises:
            FileNotFoundError: If the config file doesn't exist
            json.JSONDecodeError: If the JSON file is malformed
        """
        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
            return self.config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in configuration file: {e}", e.doc, e.pos
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self.config is None:
            self.load_config()
        return self.config.get(key, default)

    def validate_config(self) -> bool:
        """
        Validate the loaded configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if self.config is None:
            self.load_config()

        required_fields = ["catalog_path"]
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required configuration field: {field}")
        return True
