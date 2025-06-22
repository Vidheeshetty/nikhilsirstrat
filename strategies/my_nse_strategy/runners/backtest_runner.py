#!/usr/bin/env python3
"""
Backtest runner for MyNSEStrategy.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports - fix the path calculation
project_root = Path(__file__).parent.parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import logging
from typing import Dict, Any

from strategies.my_nse_strategy.strategy import MyNSEStrategy
from strategies.my_nse_strategy.config import MyNSEStrategyConfig
from backtest.shared.data_loader import DataLoader
from backtest.shared.engine import BacktestEngineManager
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Money
from nautilus_trader.model.currencies import INR


def run_backtest(config: MyNSEStrategyConfig) -> Dict[str, Any]:
    """
    Run a complete backtest with the given configuration.
    
    Args:
        config: Backtest configuration
        
    Returns:
        Dictionary containing backtest results
    """
    log = logging.getLogger(__name__)
    log.info("=== STARTING BACKTEST FOR MY_NSE_STRATEGY ===")
    
    try:
        # 1. Load data
        data_loader = DataLoader(config.catalog_path)
        instruments, ticks = data_loader.load_data(config.instrument_id)
        
        # 2. Create and configure engine
        engine_manager = BacktestEngineManager(log_level=config.log_level)
        engine = engine_manager.create_engine()
        
        # 3. Add venue
        engine_manager.add_venue(
            venue_name=config.venue_name,
            oms_type=config.venue_oms_type,
            account_type=config.venue_account_type,
            base_currency=config.venue_base_currency,
            starting_balances=[config.venue_starting_balance],
        )
        
        # 4. Add instruments
        engine_manager.add_instruments(instruments)
        
        # 5. Add data (all ticks at once)
        engine_manager.add_data(ticks)
        
        # 6. Add strategy
        if config.instrument_id:
            strategy_config = MyNSEStrategy.config_class(
                instrument_id=InstrumentId.from_str(config.instrument_id),
                position_size=1,
            )
            strategy = MyNSEStrategy(config=strategy_config)
            engine_manager.add_strategy(strategy)
        
        # 7. Run backtest
        result = engine_manager.run_backtest()
        
        # 8. Get trading results
        trading_results = engine_manager.get_trading_results()
        
        return {
            "backtest_result": result,
            "trading_results": trading_results,
            "config": config,
        }
        
    except Exception as e:
        log.error(f"Backtest failed: {e}")
        raise


def print_backtest_summary(results: Dict[str, Any]) -> None:
    """
    Print a summary of backtest results.
    
    Args:
        results: Results dictionary from run_backtest
    """
    print("\n" + "="*60)
    print("MY NSE STRATEGY - BACKTEST RESULTS SUMMARY")
    print("="*60)
    
    config = results.get("config")
    if config:
        print(f"Configuration:")
        print(f"  Catalog Path: {config.catalog_path}")
        print(f"  Instrument ID: {config.instrument_id}")
        print(f"  Venue: {config.venue_name}")
        print(f"  Starting Balance: {config.venue_starting_balance}")
    
    trading_results = results.get("trading_results", {})
    
    # Print account information
    account = trading_results.get("account")
    if account:
        print(f"\nAccount:")
        print(f"  Balance: {account.balance}")
        print(f"  Equity: {account.equity}")
        print(f"  Margin Available: {account.margin_available}")
        print(f"  Margin Used: {account.margin_used}")
    
    # Print positions
    positions = trading_results.get("positions", [])
    print(f"\nPositions ({len(positions)}):")
    for i, position in enumerate(positions):
        print(f"  {i+1}: {position}")
    
    # Print orders
    orders = trading_results.get("orders", [])
    print(f"\nOrders ({len(orders)}):")
    for i, order in enumerate(orders):
        print(f"  {i+1}: {order}")
    
    # Print trades
    trades = trading_results.get("trades", [])
    print(f"\nTrades ({len(trades)}):")
    for i, trade in enumerate(trades):
        print(f"  {i+1}: {trade}")
    
    print("\n" + "="*60)


def main():
    """Main function to run backtest for MyNSEStrategy."""
    
    # Always resolve catalog path relative to project root
    CATALOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../catalog'))
    
    # Configuration
    config = MyNSEStrategyConfig(
        catalog_path=CATALOG_PATH,
        instrument_id="BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE",
        log_level="INFO",
        venue_name="NSE",
        venue_base_currency="INR",
        venue_starting_balance=Money(1_000_000, INR),
    )
    
    # Run backtest
    try:
        results = run_backtest(config)
        print_backtest_summary(results)
        
        # Print detailed results
        print("\n=== DETAILED RESULTS ===")
        trading_results = results["trading_results"]
        
        # Print all orders
        orders = trading_results["orders"]
        print(f"\nAll Orders ({len(orders)}):")
        for i, order in enumerate(orders):
            print(f"  {i+1}: {order}")
        
        # Print all positions
        positions = trading_results["positions"]
        print(f"\nAll Positions ({len(positions)}):")
        for i, position in enumerate(positions):
            print(f"  {i+1}: {position}")
        
        # Print all trades
        trades = trading_results["trades"]
        print(f"\nAll Trades ({len(trades)}):")
        for i, trade in enumerate(trades):
            print(f"  {i+1}: {trade}")
            
    except Exception as e:
        print(f"Backtest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 