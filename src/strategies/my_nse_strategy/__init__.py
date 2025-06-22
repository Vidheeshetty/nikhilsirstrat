"""
MyNSEStrategy Package

This package contains a complete NSE (National Stock Exchange) options trading strategy
implementation with modular backtest, paper trade, and live trading capabilities.

The strategy is designed for options trading on the NSE platform, specifically targeting
BANKNIFTY options with breakout-based entry logic and comprehensive risk management.

Package Structure:
    - strategy.py: Core strategy implementation with breakout logic
    - config.py: Configuration classes for different execution modes
    - runners/: Execution runners for different trading modes
        - backtest_runner.py: Historical backtesting
        - papertrade_runner.py: Paper trading simulation
        - live_runner.py: Live trading execution

Key Features:
    - Breakout-based entry logic with rolling window analysis
    - Implied volatility and open interest filters
    - Dynamic stop-loss and take-profit management
    - Trailing stop-loss with breakeven triggers
    - End-of-day position management
    - Comprehensive metadata integration

Usage:
    from strategies.my_nse_strategy import MyNSEStrategy, MyNSEStrategyConfig
    
    # Configure strategy
    config = MyNSEStrategyConfig(
        instrument_id="BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE",
        position_size=1,
        sl_pct=0.02,
        tp_pct=0.03
    )
    
    # Create strategy instance
    strategy = MyNSEStrategy(config=config)
"""

from .strategy import MyNSEStrategy  # Import the main strategy class
from .config import MyNSEStrategyConfig  # Import the configuration class

__all__ = ["MyNSEStrategy", "MyNSEStrategyConfig"]  # Define public API

__version__ = "1.0.0"  # Package version
__author__ = "Trading Strategy Developer"  # Author information
__description__ = "NSE Options Trading Strategy with Breakout Logic"  # Package description
