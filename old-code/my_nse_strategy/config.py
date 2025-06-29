"""
Configuration Utilities for MyNSEStrategy

This module provides the main configuration class and utility functions for loading
and managing configuration from YAML files for the MyNSEStrategy.

The MyNSEStrategyConfig class extends StrategyConfig from Nautilus Trader and defines
all configurable parameters for the strategy's behavior.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from nautilus_trader.trading.strategy import StrategyConfig
from nautilus_trader.model import InstrumentId


class MyNSEStrategyConfig(StrategyConfig):
    """
    Configuration class for MyNSEStrategy parameters.

    This class defines all configurable parameters for the strategy's behavior,
    including risk management, entry/exit logic, and market filters.

    Attributes:
        instrument_id: Target instrument for trading
        meta_catalog_path: Path to metadata catalog for IV/OI data
        catalog_path: Path to the data catalog for instrument lookup and expiration checks
        sl_pct: Stop-loss percentage from entry price
        tp_pct: Take-profit percentage from entry price
        position_size: Number of contracts to trade
        end_time: Latest time to take new trades (HH:MM format)
        min_iv: Minimum implied volatility threshold
        entry_buffer_pct: Price buffer for breakout confirmation
        lookback_intervals: Rolling window size for breakout detection
        min_oi_change: Minimum open interest change threshold
        breakeven_trigger_pct: Price gain % to move SL to breakeven
        sar_enabled: Enable Stop-And-Reverse logic (future feature)
    """

    instrument_id: InstrumentId  # Target instrument ID for trading
    """Target instrument ID for trading."""

    meta_catalog_path: str = (
        "catalog-data/my_nse_strategy/catalog-meta"  # Path to metadata catalog
    )
    """Path to the Parquet metadata files containing IV/OI data."""

    catalog_path: str = "catalog-data/my_nse_strategy/catalog"  # Path to the data catalog for instrument lookup and expiration checks
    """Path to the data catalog for instrument lookup and expiration checks."""

    sl_pct: float = 0.02  # 2% stop-loss default
    """Stop-loss percentage from entry price (2% default)."""

    tp_pct: float = 0.03  # 3% take-profit default
    """Take-profit target as a percentage from entry price (3% default)."""

    position_size: int = 1  # Default position size
    """Number of contracts to trade per position."""

    end_time: str = "15:15"  # End time for new trades
    """Latest time to take new trades in HH:MM format."""

    min_iv: float = 0  # Minimum implied volatility threshold
    """Minimum implied volatility filter threshold."""

    entry_buffer_pct: float = 0.01  # 1% entry buffer
    """Entry trigger buffer percentage for breakout confirmation."""

    lookback_intervals: int = 2  # Rolling window size
    """Rolling window size for price breakout detection."""

    min_oi_change: float = -100  # Minimum open interest change
    """Minimum open interest change threshold for entry filtering."""

    breakeven_trigger_pct: float = 2  # 2% breakeven trigger
    """Price gain percentage to move stop-loss to breakeven."""

    sar_enabled: bool = True  # Stop-and-reverse flag
    """Enable Stop-And-Reverse logic (reserved for future implementation)."""


def load_config_from_file(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_file: Path to the YAML configuration file

    Returns:
        Dictionary containing configuration parameters

    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, "r") as file:
        try:
            config = yaml.safe_load(file)
            return config or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {config_file}: {e}")


def get_default_config_path() -> str:
    """
    Get the default configuration file path.

    Returns:
        Path to the default strategy.yaml configuration file
    """
    return str(Path(__file__).parent / "strategy.yaml")


def load_default_config() -> Dict[str, Any]:
    """
    Load configuration from the default strategy.yaml file.

    Returns:
        Dictionary containing configuration parameters

    Raises:
        FileNotFoundError: If the default config file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    config_path = get_default_config_path()
    return load_config_from_file(config_path)


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration parameters.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["instrument_id"]

    for field in required_fields:
        if field not in config or config[field] is None:
            raise ValueError(
                f"Required configuration field '{field}' is missing or None"
            )

    # Validate instrument_id format
    instrument_id = config["instrument_id"]
    if not isinstance(instrument_id, str) or "." not in instrument_id:
        raise ValueError(f"Invalid instrument_id format: {instrument_id}")

    # Validate numeric fields
    numeric_fields = [
        "sl_pct",
        "tp_pct",
        "position_size",
        "min_iv",
        "entry_buffer_pct",
        "lookback_intervals",
        "min_oi_change",
        "breakeven_trigger_pct",
    ]

    for field in numeric_fields:
        if field in config and config[field] is not None:
            try:
                float(config[field])
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid numeric value for '{field}': {config[field]}"
                )

    return True
