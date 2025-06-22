"""
Configuration Module for MyNSEStrategy

This module contains configuration classes for the MyNSEStrategy, providing
flexible parameter management for different execution modes (backtest, paper trade, live).

The configuration system allows for easy customization of strategy parameters
without modifying the core strategy logic, enabling rapid experimentation and
optimization across different market conditions.

Classes:
    MyNSEStrategyConfig: Main configuration class for strategy parameters
"""

from dataclasses import dataclass, field  # Import dataclass utilities
from typing import Optional, List  # Import type hints
from nautilus_trader.model.identifiers import InstrumentId, Venue  # Import trading identifiers
from nautilus_trader.model.enums import AccountType, OmsType  # Import trading enums
from nautilus_trader.model.objects import Money  # Import money object
from nautilus_trader.model.currencies import INR  # Import INR currency


@dataclass
class MyNSEStrategyConfig:
    """
    Configuration class for MyNSEStrategy execution parameters.
    
    This class encapsulates all configurable parameters for the strategy,
    including data sources, venue settings, risk management, and execution logic.
    
    Attributes:
        catalog_path: Path to the data catalog containing historical data
        instrument_id: Target instrument ID for trading (e.g., "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE")
        venue_name: Trading venue name (default: "NSE")
        venue_oms_type: Order management system type (default: NETTING)
        venue_account_type: Account type for margin calculations (default: MARGIN)
        venue_base_currency: Base currency for the trading account (default: "INR")
        venue_starting_balance: Initial account balance for backtesting
        log_level: Logging level for strategy execution (default: "INFO")
        bypass_logging: Flag to bypass detailed logging for performance (default: False)
    """
    
    # Data Configuration
    catalog_path: str = "catalog-data/my_nse_strategy/catalog"  # Default catalog path for historical data
    """Path to the data catalog containing historical market data."""
    
    instrument_id: Optional[str] = None  # Target instrument ID for trading
    """Target instrument ID for trading. Format: 'SYMBOL.OPT.EXPIRY.STRIKE.TYPE.EXCHANGE'"""
    
    # Venue Configuration
    venue_name: str = "NSE"  # Default trading venue
    """Trading venue name (National Stock Exchange)."""
    
    venue_oms_type: OmsType = OmsType.NETTING  # Order management system type
    """Order management system type - NETTING for single position per instrument."""
    
    venue_account_type: AccountType = AccountType.MARGIN  # Account type for margin calculations
    """Account type for margin calculations and position management."""
    
    venue_base_currency: str = "INR"  # Base currency for trading account
    """Base currency for the trading account (Indian Rupees)."""
    
    venue_starting_balance: Money = field(default_factory=lambda: Money(1_000_000, INR))  # 1 million INR starting balance
    """Initial account balance for backtesting (1 million INR)."""
    
    # Logging Configuration
    log_level: str = "INFO"  # Default logging level
    """Logging level for strategy execution and debugging."""
    
    bypass_logging: bool = False  # Flag to bypass detailed logging
    """Flag to bypass detailed logging for performance optimization."""
    
    # Strategy configuration
    strategy_config: Optional[dict] = None
    
    # Time configuration
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.instrument_id and not isinstance(self.instrument_id, str):
            raise ValueError("instrument_id must be a string")
        
        if self.start_time and self.end_time:
            # Add validation for time format if needed
            pass


@dataclass
class VenueConfig:
    """Configuration for a trading venue."""
    
    name: str
    oms_type: OmsType = OmsType.NETTING
    account_type: AccountType = AccountType.MARGIN
    base_currency: str = "INR"
    starting_balances: List[Money] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default starting balances if not provided."""
        if not self.starting_balances:
            self.starting_balances = [Money(1_000_000, INR)]


@dataclass
class DataConfig:
    """Configuration for data loading."""
    
    catalog_path: str
    instrument_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    def __post_init__(self):
        """Validate data configuration."""
        if not self.catalog_path:
            raise ValueError("catalog_path is required") 