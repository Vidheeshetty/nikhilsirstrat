#!/usr/bin/env python3
"""
Test script to verify enhanced results with account details.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append('src')

def test_enhanced_results():
    """Test enhanced results with account details."""
    print("Testing enhanced results with account details...")
    print("=" * 60)
    
    try:
        from strategies.my_nse_strategy.runners.backtest import BacktestOrchestrator
        
        # Configuration
        config_file = "src/strategies/my_nse_strategy/config/strategy.yaml"
        
        # Create orchestrator
        orchestrator = BacktestOrchestrator(config_file)
        
        # Test with a single instrument
        instrument_id = "NIFTY.OPT.03Jul2025.22800.CALL.NSE"
        
        print(f"Running backtest for: {instrument_id}")
        result = orchestrator.run_single_backtest(instrument_id)
        
        print(f"\nEnhanced Results:")
        print(f"  Instrument ID: {result.get('instrument_id', 'N/A')}")
        print(f"  Total Orders: {result.get('total_orders', 0)}")
        print(f"  Total Positions: {result.get('total_positions', 0)}")
        print(f"  Total Trades: {result.get('total_trades', 0)}")
        print(f"  Total Investment: {result.get('total_investment', 'N/A')}")
        print(f"  PnL Total: {result.get('pnl_total', 'N/A')}")
        print(f"  PnL %: {result.get('pnl_pct_total', 'N/A')}")
        print(f"  Starting Balance: {result.get('starting_balance', 0.0):,.2f}")
        print(f"  Ending Balance: {result.get('ending_balance', 0.0):,.2f}")
        print(f"  Free Balance: {result.get('balance_free', 0.0):,.2f}")
        print(f"  Locked Balance: {result.get('balance_locked', 0.0):,.2f}")
        print(f"  Account ID: {result.get('account_id', 'N/A')}")
        print(f"  Base Currency: {result.get('base_currency', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"Error testing enhanced results: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_results()
    sys.exit(0 if success else 1) 