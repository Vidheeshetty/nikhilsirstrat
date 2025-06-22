#!/usr/bin/env python3
"""
Simple Backtest Runner for MyNSEStrategy

This module provides a simplified backtesting interface that reads configuration
from YAML and allows command-line overrides.

Usage:
    # Run with default config
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE"
    
    # Override specific parameters
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --start_time "2025-06-18T12:00:00"
    
    # Use custom config file
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --config_file "custom_config.yaml"
"""

import sys
import os
from pathlib import Path
import argparse
import yaml
from datetime import datetime

# Add parent directories to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from nautilus_trader.backtest.config import (
    BacktestVenueConfig, BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig
)
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.currencies import INR


def load_config_from_file(config_file: str) -> dict:
    """Load strategy configuration from a YAML file."""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        return config or {}


def run_backtest(config_file: str = None, **overrides):
    """
    Run a backtest with configuration from YAML and optional overrides.
    
    Args:
        config_file: Optional path to YAML configuration file
        **overrides: Command-line parameter overrides
    """
    # Load from YAML file
    if config_file:
        config = load_config_from_file(config_file)
    else:
        # Use default config file
        default_config_path = Path(__file__).parent.parent / "config" / "strategy.yaml"
        if not default_config_path.exists():
            raise FileNotFoundError(f"Default configuration file not found: {default_config_path}")
        config = load_config_from_file(str(default_config_path))
    
    # Apply command-line overrides
    config.update(overrides)
    
    # Validate required fields
    if 'instrument_id' not in config:
        raise ValueError("instrument_id is required (either in YAML or command-line)")
    
    instrument_id = config['instrument_id']
    print(f"=== STARTING BACKTEST FOR {instrument_id} ===")
    print(f"Start Time: {config.get('start_time', 'Not specified')}")
    print(f"End Time: {config.get('end_time', 'Not specified')}")
    print(f"Catalog Path: {config.get('catalog_path', 'catalog-data/my_nse_strategy/catalog')}")
    
    # 1. Venue config
    venue = BacktestVenueConfig(
        name="NSE",
        oms_type="NETTING",
        account_type="MARGIN",
        starting_balances=["1000000 INR"],
        base_currency="INR"
    )
    
    # 2. Data config
    data = BacktestDataConfig(
        catalog_path=config.get('catalog_path', 'catalog-data/my_nse_strategy/catalog'),
        data_cls="nautilus_trader.model.data:QuoteTick",
        instrument_id=InstrumentId.from_str(instrument_id),
        start_time=config.get('start_time', '2025-06-18T12:00:00'),
        end_time=config.get('end_time', '2025-06-18T14:15:00')
    )
    
    # 3. Engine config - pass all config parameters to strategy
    strategy_config = {
        "instrument_id": instrument_id,
        "sl_pct": config.get('sl_pct', 0.02),
        "tp_pct": config.get('tp_pct', 0.03),
        "position_size": config.get('position_size', 1),
        "min_iv": config.get('min_iv', 0),
        "entry_buffer_pct": config.get('entry_buffer_pct', 0.01),
        "lookback_intervals": config.get('lookback_intervals', 2),
        "min_oi_change": config.get('min_oi_change', -100),
        "breakeven_trigger_pct": config.get('breakeven_trigger_pct', 2),
        "sar_enabled": config.get('sar_enabled', True),
        "atm_window": config.get('atm_window', "15min"),
        "meta_catalog_path": config.get('meta_catalog_path', 'catalog-data/my_nse_strategy/catalog-meta'),
    }
    
    engine = BacktestEngineConfig(
        strategies=[
            ImportableStrategyConfig(
                strategy_path="strategies.my_nse_strategy.strategy:MyNSEStrategy",
                config_path="strategies.my_nse_strategy.strategy:MyNSEStrategyConfig",
                config=strategy_config
            )
        ]
    )
    
    # 4. Run config
    run_config = BacktestRunConfig(
        venues=[venue],
        data=[data],
        engine=engine
    )
    
    # 5. Run the backtest
    node = BacktestNode(configs=[run_config])
    print("Backtest node initialized successfully")
    
    print("Starting backtest execution...")
    results = node.run()
    
    # Print results
    print("\n=== BACKTEST RESULTS ===")
    for result in results:
        print(f"Run ID: {getattr(result, 'id', 'N/A')}")
        print(f"Total P&L: {getattr(result, 'total_pnl', 'N/A')}")
        print(f"Total Trades: {getattr(result, 'total_trades', 'N/A')}")
    print("=== BACKTEST COMPLETED ===")
    
    return node


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Run MyNSEStrategy backtest with YAML config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config (reads from config/strategy.yaml)
  python backtest_runner.py
  
  # Override instrument_id
  python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE"
  
  # Override specific parameters
  python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --start_time "2025-06-18T12:00:00"
  
  # Use custom config file
  python backtest_runner.py --config_file "custom_config.yaml"
        """
    )
    
    # Optional arguments
    parser.add_argument(
        "--instrument_id",
        type=str,
        help="Instrument ID to trade (overrides YAML)"
    )
    
    parser.add_argument(
        "--config_file",
        type=str,
        help="Path to YAML configuration file (default: config/strategy.yaml)"
    )
    
    parser.add_argument(
        "--start_time",
        type=str,
        help="Backtest start time in ISO format (overrides YAML)"
    )
    
    parser.add_argument(
        "--end_time",
        type=str,
        help="Backtest end time in ISO format (overrides YAML)"
    )
    
    parser.add_argument(
        "--position_size",
        type=int,
        help="Position size in contracts (overrides YAML)"
    )
    
    parser.add_argument(
        "--sl_pct",
        type=float,
        help="Stop-loss percentage (overrides YAML)"
    )
    
    parser.add_argument(
        "--tp_pct",
        type=float,
        help="Take-profit percentage (overrides YAML)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Collect overrides (only non-None values)
    overrides = {}
    for key, value in vars(args).items():
        if value is not None and key != 'config_file':
            overrides[key] = value
    
    try:
        # Run the backtest
        node = run_backtest(
            config_file=args.config_file,
            **overrides
        )
        
        print("Backtest completed successfully!")
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 