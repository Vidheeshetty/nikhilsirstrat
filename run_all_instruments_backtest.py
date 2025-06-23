#!/usr/bin/env python3
"""
Script to run backtests for all instruments with enhanced logging and tabular results.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append('src')

def main():
    """Run backtests for all instruments."""
    print("Starting backtest for all instruments...")
    print("=" * 60)
    
    try:
        from strategies.my_nse_strategy.runners.backtest import BacktestOrchestrator
        
        # Configuration
        config_file = "src/strategies/my_nse_strategy/config/strategy.yaml"
        
        # Create orchestrator
        orchestrator = BacktestOrchestrator(config_file)
        
        # Get all available instruments
        data_manager = orchestrator.data_manager
        all_instruments = data_manager.get_all_instrument_ids()
        
        print(f"Found {len(all_instruments)} instruments for backtesting")
        print("First 5 instruments:")
        for i, instrument in enumerate(all_instruments[:5]):
            print(f"  {i+1}. {instrument}")
        
        if len(all_instruments) > 5:
            print(f"  ... and {len(all_instruments) - 5} more instruments")
        
        # Confirm with user
        response = input(f"\nProceed with backtesting {len(all_instruments)} instruments? (y/N): ")
        if response.lower() != 'y':
            print("Backtest cancelled by user.")
            return
        
        # Run backtest for all instruments
        print(f"\nStarting batch backtest for {len(all_instruments)} instruments...")
        results = orchestrator.run_all_instruments_backtest()
        
        print(f"\nBacktest completed!")
        print(f"Successfully tested: {len(results)} instruments")
        
        # Show summary
        if results:
            total_pnl = 0.0
            total_trades = 0
            profitable_count = 0
            
            for result in results:
                try:
                    pnl_str = result.get('pnl_total', '0.00')
                    pnl = float(pnl_str.replace(',', '')) if isinstance(pnl_str, str) else float(pnl_str)
                    total_pnl += pnl
                    total_trades += result.get('total_trades', 0)
                    if pnl > 0:
                        profitable_count += 1
                except (ValueError, TypeError):
                    pass
            
            print(f"\nQuick Summary:")
            print(f"  Total PnL: {total_pnl:,.2f} INR")
            print(f"  Total Trades: {total_trades}")
            print(f"  Profitable Instruments: {profitable_count}/{len(results)}")
            print(f"  Win Rate: {(profitable_count/len(results)*100):.2f}%")
        
        print(f"\nCheck the _summary.txts directory for detailed results.")
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 