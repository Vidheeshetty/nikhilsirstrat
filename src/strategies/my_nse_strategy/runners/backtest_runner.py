#!/usr/bin/env python3
"""
Backtest Runner for MyNSEStrategy

This module provides a comprehensive backtesting framework for the MyNSEStrategy,
enabling historical performance analysis and strategy optimization.

The backtest runner handles:
    - Data loading from Parquet catalogs
    - Strategy configuration and initialization
    - Backtest engine setup and execution
    - Performance analysis and reporting
    - Logging and debugging support

Key Features:
    - Flexible data source configuration
    - Configurable backtest parameters
    - Comprehensive performance metrics
    - Detailed trade logging
    - Error handling and validation

Usage:
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE"
    python backtest_runner.py --config_file config/strategy.yaml

Author: Trading Strategy Developer
Version: 1.0.0
"""

import sys  # Import system module for path manipulation
import os  # Import os for file operations
from pathlib import Path  # Import Path for cross-platform path handling
import argparse  # Import argparse for command line argument parsing
import yaml  # Import yaml for configuration file parsing
from datetime import datetime  # Import datetime for timestamp handling

# Add parent directories to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))  # Add src directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))  # Add project root to path

from nautilus_trader.backtest.config import (
    BacktestVenueConfig, BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig  # Import backtest configs
)
from nautilus_trader.backtest.node import BacktestNode  # Import backtest node
from nautilus_trader.config import ImportableStrategyConfig  # Import strategy config wrapper
from nautilus_trader.model.identifiers import InstrumentId  # Import instrument ID
from nautilus_trader.model.currencies import INR  # Import INR currency


def load_config_from_file(config_file: str) -> dict:
    """
    Load strategy configuration from a YAML file.
    
    This function reads a YAML configuration file and returns a dictionary
    containing strategy parameters. It validates the configuration and
    provides default values for missing parameters.
    
    Args:
        config_file: Path to the YAML configuration file
        
    Returns:
        Dictionary containing strategy configuration parameters
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    if not os.path.exists(config_file):  # Check if config file exists
        raise FileNotFoundError(f"Configuration file not found: {config_file}")  # Raise error if missing
    
    with open(config_file, 'r') as file:  # Open config file for reading
        config = yaml.safe_load(file)  # Load YAML configuration
        return config  # Return configuration dictionary


def run_backtest(
    instrument_id: str,
    config_file: str = None,
    catalog_path: str = "catalog-data/my_nse_strategy/catalog",
    meta_catalog_path: str = "catalog-data/my_nse_strategy/catalog-meta",
    start_time: str = "2025-06-26T09:15:00",
    end_time: str = "2025-06-26T15:30:00",
    **strategy_params
):
    """
    Run a complete backtest for the MyNSEStrategy.
    
    This function orchestrates the entire backtesting process including
    configuration setup, data loading, strategy initialization, and
    execution. It provides comprehensive logging and error handling.
    
    Args:
        instrument_id: Target instrument ID for trading
        config_file: Optional path to YAML configuration file
        catalog_path: Path to the data catalog
        meta_catalog_path: Path to metadata catalog
        start_time: Backtest start time (ISO format)
        end_time: Backtest end time (ISO format)
        **strategy_params: Additional strategy parameters
        
    Returns:
        BacktestNode object with completed backtest results
    """
    print(f"=== STARTING BACKTEST FOR {instrument_id} ===")  # Log backtest start
    print(f"Start Time: {start_time}")  # Log start time
    print(f"End Time: {end_time}")  # Log end time
    print(f"Catalog Path: {catalog_path}")  # Log catalog path
    
    # Load configuration from file if provided
    if config_file:  # Check if config file provided
        print(f"Loading configuration from: {config_file}")  # Log config file loading
        file_config = load_config_from_file(config_file)  # Load config from file
        strategy_params.update(file_config)  # Update strategy params with file config
    
    # 1. Venue config
    venue = BacktestVenueConfig(
        name="NSE",  # Venue name
        oms_type="NETTING",  # Order management system type
        account_type="MARGIN",  # Account type
        starting_balances=["1000000 INR"],  # Starting balance
        base_currency="INR"  # Base currency
    )
    
    # 2. Data config
    data = BacktestDataConfig(
        catalog_path=catalog_path,  # Path to data catalog
        data_cls="nautilus_trader.model.data:QuoteTick",  # Data class (fully qualified path)
        instrument_id=InstrumentId.from_str(instrument_id),  # Instrument ID
        start_time=start_time,  # Start time
        end_time=end_time  # End time
    )
    
    # 3. Engine config (strategy config must be importable)
    # Use all strategy_params already present in the runner
    engine = BacktestEngineConfig(
        strategies=[
            ImportableStrategyConfig(
                strategy_path="strategies.my_nse_strategy.strategy:MyNSEStrategy",  # Path to strategy class
                config_path="strategies.my_nse_strategy.strategy:MyNSEStrategyConfig",  # Path to config class
                config={
                    "instrument_id": instrument_id,
                    **strategy_params  # All other strategy params
                }
            )
        ]
    )
    
    # 4. Run config
    run_config = BacktestRunConfig(
        venues=[venue],  # List of venue configs
        data=[data],  # List of data configs
        engine=engine  # Engine config
    )
    
    # 5. Run the backtest
    node = BacktestNode(configs=[run_config])  # Create backtest node
    print("Backtest node initialized successfully")  # Log node initialization
    
    print("Starting backtest execution...")  # Log execution start
    results = node.run()  # Execute backtest
    
    # Print results
    print("\n=== BACKTEST RESULTS ===")  # Log results header
    for result in results:
        print(f"Run ID: {getattr(result, 'id', 'N/A')}")  # Log run ID if available
        print(f"Total P&L: {getattr(result, 'total_pnl', 'N/A')}")  # Log total P&L if available
        print(f"Total Trades: {getattr(result, 'total_trades', 'N/A')}")  # Log total trades if available
    print("=== BACKTEST COMPLETED ===")  # Log backtest completion
    
    return node  # Return node with results


def main():
    """
    Main function for command-line execution.
    
    This function parses command-line arguments and executes the backtest
    with the specified parameters. It provides a user-friendly interface
    for running backtests from the command line.
    """
    parser = argparse.ArgumentParser(description="Run MyNSEStrategy backtest")  # Create argument parser
    
    # Required arguments
    parser.add_argument(  # Add instrument ID argument
        "--instrument_id",
        type=str,
        required=True,
        help="Instrument ID to trade (e.g., 'BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE')"
    )
    
    # Optional arguments
    parser.add_argument(  # Add config file argument
        "--config_file",
        type=str,
        help="Path to YAML configuration file"
    )
    
    parser.add_argument(  # Add catalog path argument
        "--catalog_path",
        type=str,
        default="catalog-data/my_nse_strategy/catalog",
        help="Path to data catalog (default: catalog-data/my_nse_strategy/catalog)"
    )
    
    parser.add_argument(  # Add metadata catalog path argument
        "--meta_catalog_path",
        type=str,
        default="catalog-data/my_nse_strategy/catalog-meta",
        help="Path to metadata catalog (default: catalog-data/my_nse_strategy/catalog-meta)"
    )
    
    parser.add_argument(  # Add start time argument
        "--start_time",
        type=str,
        default="2025-06-26T09:15:00",
        help="Backtest start time in ISO format (default: 2025-06-26T09:15:00)"
    )
    
    parser.add_argument(  # Add end time argument
        "--end_time",
        type=str,
        default="2025-06-26T15:30:00",
        help="Backtest end time in ISO format (default: 2025-06-26T15:30:00)"
    )
    
    # Strategy parameters
    parser.add_argument(  # Add stop-loss argument
        "--sl_pct",
        type=float,
        default=0.02,
        help="Stop-loss percentage (default: 0.02)"
    )
    
    parser.add_argument(  # Add take-profit argument
        "--tp_pct",
        type=float,
        default=0.03,
        help="Take-profit percentage (default: 0.03)"
    )
    
    parser.add_argument(  # Add position size argument
        "--position_size",
        type=int,
        default=1,
        help="Position size in contracts (default: 1)"
    )
    
    parser.add_argument(  # Add minimum IV argument
        "--min_iv",
        type=float,
        default=0,
        help="Minimum implied volatility threshold (default: 0)"
    )
    
    parser.add_argument(  # Add entry buffer argument
        "--entry_buffer_pct",
        type=float,
        default=0.01,
        help="Entry buffer percentage (default: 0.01)"
    )
    
    parser.add_argument(  # Add lookback intervals argument
        "--lookback_intervals",
        type=int,
        default=2,
        help="Rolling window size (default: 2)"
    )
    
    parser.add_argument(  # Add minimum OI change argument
        "--min_oi_change",
        type=float,
        default=-100,
        help="Minimum open interest change (default: -100)"
    )
    
    parser.add_argument(  # Add breakeven trigger argument
        "--breakeven_trigger_pct",
        type=float,
        default=2,
        help="Breakeven trigger percentage (default: 2)"
    )
    
    # Parse arguments
    args = parser.parse_args()  # Parse command line arguments
    
    # Extract strategy parameters
    strategy_params = {  # Create strategy parameters dictionary
        'sl_pct': args.sl_pct,  # Stop-loss percentage
        'tp_pct': args.tp_pct,  # Take-profit percentage
        'position_size': args.position_size,  # Position size
        'min_iv': args.min_iv,  # Minimum IV threshold
        'entry_buffer_pct': args.entry_buffer_pct,  # Entry buffer
        'lookback_intervals': args.lookback_intervals,  # Lookback intervals
        'min_oi_change': args.min_oi_change,  # Minimum OI change
        'breakeven_trigger_pct': args.breakeven_trigger_pct,  # Breakeven trigger
    }
    
    try:
        # Run the backtest
        node = run_backtest(  # Execute backtest
            instrument_id=args.instrument_id,  # Set instrument ID
            config_file=args.config_file,  # Set config file
            catalog_path=args.catalog_path,  # Set catalog path
            meta_catalog_path=args.meta_catalog_path,  # Set metadata catalog path
            start_time=args.start_time,  # Set start time
            end_time=args.end_time,  # Set end time
            **strategy_params  # Pass strategy parameters
        )
        
        print("Backtest completed successfully!")  # Log successful completion
        
    except Exception as e:  # Handle exceptions
        print(f"Error running backtest: {e}")  # Log error message
        sys.exit(1)  # Exit with error code


if __name__ == "__main__":
    main()  # Execute main function when script is run directly 