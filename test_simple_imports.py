#!/usr/bin/env python3
"""
Simple import test to isolate issues.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_backtest_utils():
    print("Testing backtest_utils imports...")
    try:
        from src.backtest_utils.config_loader import BacktestConfigLoader
        print("✓ BacktestConfigLoader imported")
        
        from src.backtest_utils.data_loader import DataLoader
        print("✓ DataLoader imported")
        
        from src.backtest_utils.engine_launcher import BacktestEngineLauncher
        print("✓ BacktestEngineLauncher imported")
        
        from src.backtest_utils.results_aggregator import ResultsAggregator
        print("✓ ResultsAggregator imported")
        
        return True
    except Exception as e:
        print(f"✗ Backtest utils import error: {e}")
        return False

def test_strategy():
    print("\nTesting strategy imports...")
    try:
        from src.strategies.my_nse_strategy import MyNSEStrategy, MyNSEStrategyConfig
        print("✓ Strategy imported")
        return True
    except Exception as e:
        print(f"✗ Strategy import error: {e}")
        return False

def test_runner():
    print("\nTesting runner imports...")
    try:
        from src.strategies.my_nse_strategy.runners.backtest_runner import MyNSEBacktestRunner
        print("✓ Backtest runner imported")
        return True
    except Exception as e:
        print(f"✗ Runner import error: {e}")
        return False

if __name__ == "__main__":
    test_backtest_utils()
    test_strategy()
    test_runner() 