#!/usr/bin/env python3
"""
Paper Trading Setup Script

Quick setup script to configure and test paper trading infrastructure.
"""

import sys
import yaml
from pathlib import Path
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_basic_config():
    """Create a basic paper trading configuration."""
    config = {
        "engine": {
            "trader_id": "PAPER_TRADER-001",
            "strategy_id": "PAPER_STRATEGY-001",
            "venue": "NSE",
            "log_level": "INFO",
        },
        "brokers": {
            "zerodha": {
                "broker_name": "zerodha",
                "paper_trading": True,
                "api_key": "paper_key",
                "api_secret": "paper_secret",
                "paper_initial_balance": 1000000.0,
                "paper_brokerage_per_order": 20.0,
                "paper_stt_rate": 0.025,
                "paper_transaction_charges": 0.00325,
                "max_position_size": 100,
                "max_daily_loss": 50000.0,
                "max_open_positions": 10,
                "log_level": "INFO",
                "log_orders": True,
                "log_trades": True,
            }
        },
        "strategies": {
            "trend_riding": {
                "enabled": False,  # Disabled by default since config may not exist
                "broker": "zerodha",
                "config_file": "src/strategies/trend_riding/config.yaml",
            }
        },
        "data_feed": {
            "type": "paper",
            "update_frequency": 1,
            "market_start_time": "09:15",
            "market_end_time": "15:30",
            "trading_days": [0, 1, 2, 3, 4],
        },
        "risk_management": {
            "global_max_daily_loss": 100000.0,
            "global_max_positions": 20,
            "position_size_limit": 0.05,
            "emergency_stop_loss": 0.10,
            "max_drawdown_limit": 0.15,
        },
        "reporting": {
            "realtime_updates": True,
            "update_frequency": 5,
            "eod_report": True,
            "formats": ["json", "csv", "html"],
            "output_dir": "runlogs/papertrading",
            "metrics": ["pnl", "positions", "orders", "trades", "drawdown", "win_rate"],
        },
        "logging": {
            "level": "INFO",
            "file": "runlogs/papertrading/paper_trading.log",
            "max_file_size": "10MB",
            "backup_count": 5,
        },
    }
    return config


def setup_directories():
    """Create necessary directories."""
    directories = ["config", "runlogs/papertrading", "src/brokers", "utils/reporting"]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def create_config_file(config_path: str):
    """Create configuration file."""
    config = create_basic_config()

    with open(config_path, "w") as f:
        yaml.dump(config, f, indent=2, default_flow_style=False)

    print(f"✓ Created configuration file: {config_path}")


def test_imports():
    """Test that all required modules can be imported."""
    try:
        from src.brokers.base import BaseBroker, BrokerConfig

        print("✓ Base broker modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def check_strategy_configs():
    """Check if strategy configuration files exist."""
    strategy_configs = [
        "src/strategies/trend_riding/config.yaml",
        "src/strategies/swing_range_expansion/config.yaml",
    ]

    for config_file in strategy_configs:
        if Path(config_file).exists():
            print(f"✓ Found strategy config: {config_file}")
        else:
            print(f"⚠ Strategy config not found: {config_file}")
            print("  You may need to create this file or disable the strategy")


def print_next_steps():
    """Print next steps for the user."""
    print("\n" + "=" * 60)
    print("PAPER TRADING SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the configuration file: config/paper_trading.yaml")
    print("2. Customize broker settings and risk parameters as needed")
    print("3. Enable strategies by setting 'enabled: true' in config")
    print("4. Ensure strategy configuration files exist")
    print("5. Run paper trading:")
    print("   python scripts/run_paper_trading.py")
    print(
        "\nFor detailed documentation, see: documentation/paper-trading/PAPER_TRADING_SETUP.md"
    )
    print("\nExample commands:")
    print("  # Test broker connection")
    print(
        "  python -c \"from src.brokers.zerodha.config import ZerodhaConfig; print('✓ Broker modules working')\""
    )
    print("")
    print("  # Run paper trading (when strategies are configured)")
    print("  python scripts/run_paper_trading.py")


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Paper Trading Setup")
    parser.add_argument(
        "--config", default="config/paper_trading.yaml", help="Configuration file path"
    )
    parser.add_argument(
        "--skip-test", action="store_true", help="Skip functionality test"
    )

    args = parser.parse_args()

    print("Setting up paper trading infrastructure...")
    print("=" * 50)

    # Setup directories
    setup_directories()

    # Create configuration file
    create_config_file(args.config)

    # Test imports
    if not test_imports():
        print("\n✗ Setup failed: Import errors detected")
        print("Please ensure all required files are in place")
        return 1

    # Check strategy configs
    check_strategy_configs()

    # Print next steps
    print_next_steps()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
