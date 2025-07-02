#!/usr/bin/env python3
"""
Test script to verify the modularization of the backtest framework.

This script tests that all the new modular components can be imported
and used correctly.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")

    try:
        # Test backtest_utils imports
        from src.backtest_utils import (
            BacktestConfigLoader,
            DataLoader,
            BacktestEngineLauncher,
            ResultsAggregator,
            BatchBacktestRunner,
            BatchHelpers,
        )

        print("✓ All backtest_utils modules imported successfully")

        # Test strategy imports
        from src.strategies.my_nse_strategy import MyNSEStrategy, MyNSEStrategyConfig

        print("✓ Strategy modules imported successfully")

        # Test runner imports
        from src.strategies.my_nse_strategy.runners.backtest_runner import (
            MyNSEBacktestRunner,
        )

        print("✓ Backtest runner imported successfully")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_config_loader():
    """Test the configuration loader functionality."""
    print("\nTesting configuration loader...")

    try:
        from src.backtest_utils import BacktestConfigLoader

        # Test loading config
        config_loader = BacktestConfigLoader("config/backtest_config.json")
        config = config_loader.load_config()

        if config:
            print("✓ Configuration loaded successfully")
            print(f"  - Catalog path: {config.get('catalog_path', 'Not found')}")
            print(f"  - Output dir: {config.get('output_dir', 'Not found')}")
            return True
        else:
            print("✗ Configuration is empty")
            return False

    except Exception as e:
        print(f"✗ Configuration loader error: {e}")
        return False


def test_strategy_config():
    """Test the strategy configuration."""
    print("\nTesting strategy configuration...")

    try:
        from src.strategies.my_nse_strategy import MyNSEStrategyConfig
        from nautilus_trader.model import InstrumentId

        # Create a test configuration with correct parameters
        config = MyNSEStrategyConfig(
            instrument_id=InstrumentId.from_str("NIFTY-INDEX.NSE"),
            position_size=1,
            sl_pct=0.02,
            tp_pct=0.03,
            lookback_intervals=2,
            entry_buffer_pct=0.01,
            min_iv=0.0,
            min_oi_change=-100,
            breakeven_trigger_pct=2.0,
            sar_enabled=True,
        )

        print("✓ Strategy configuration created successfully")
        print(f"  - Instrument: {config.instrument_id}")
        print(f"  - Position size: {config.position_size}")
        print(f"  - Stop loss: {config.sl_pct}%")
        print(f"  - Take profit: {config.tp_pct}%")
        print(f"  - Lookback intervals: {config.lookback_intervals}")

        return True

    except Exception as e:
        print(f"✗ Strategy configuration error: {e}")
        return False


def test_backtest_runner():
    """Test the backtest runner initialization."""
    print("\nTesting backtest runner...")

    try:
        from src.strategies.my_nse_strategy.runners.backtest_runner import (
            MyNSEBacktestRunner,
        )

        # Initialize the runner
        runner = MyNSEBacktestRunner("config/backtest_config.json")

        print("✓ Backtest runner initialized successfully")
        print(f"  - Config loader: {type(runner.config_loader).__name__}")
        print(f"  - Data loader: {type(runner.data_loader).__name__}")
        print(f"  - Engine launcher: {type(runner.engine_launcher).__name__}")
        print(f"  - Results aggregator: {type(runner.results_aggregator).__name__}")

        return True

    except Exception as e:
        print(f"✗ Backtest runner error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Modularization of Backtest Framework")
    print("=" * 60)

    tests = [
        test_imports,
        test_config_loader,
        test_strategy_config,
        test_backtest_runner,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed! Modularization is working correctly.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
