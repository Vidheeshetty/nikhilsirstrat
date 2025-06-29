#!/usr/bin/env python3
"""
Debug script to check fills report data
"""

import sys
import os
from pathlib import Path
import pandas as pd

# Add parent directories to Python path for imports
sys.path.append(str(Path(__file__).parent))

from nautilus_trader.backtest.config import (
    BacktestVenueConfig,
    BacktestDataConfig,
    BacktestEngineConfig,
    BacktestRunConfig,
)
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.currencies import INR
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.enums import OmsType, AccountType, BookType
from nautilus_trader.model.objects import Money, Currency

# Import strategy
from src.strategies.my_nse_strategy.strategy import MyNSEStrategy
from src.strategies.my_nse_strategy.config import MyNSEStrategyConfig


def debug_fills_report():
    """Debug the fills report to see what data is available."""

    # Load configuration
    config_file = "src/strategies/my_nse_strategy/config/strategy.yaml"
    with open(config_file, "r") as f:
        import yaml

        config = yaml.safe_load(f)

    instrument_id = "NIFTY.OPT.03Jul2025.22800.CALL.NSE"
    config["instrument_id"] = instrument_id

    # Create catalog
    catalog = ParquetDataCatalog("catalog-data/my_nse_strategy/catalog")

    # Create backtest engine
    engine = BacktestEngine(
        config=BacktestEngineConfig(trader_id="BACKTESTER-001"),
    )

    # Add venue before adding instrument
    engine.add_venue(
        venue=Venue("NSE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(1_000_000, INR)],
        base_currency=INR,
        book_type=BookType.L1_MBP,
    )

    # Add instruments
    instruments = catalog.instruments(
        instrument_ids=[config["instrument_id"]],
        as_nautilus=True,
    )
    engine.add_instrument(instruments[0])

    # Add data
    data = catalog.quote_ticks(
        instrument_ids=[config["instrument_id"]],
        start=config.get("start_time"),
        end=config.get("end_time"),
        as_nautilus=True,
    )
    engine.add_data(data)

    # Prepare config for MyNSEStrategyConfig
    config["instrument_id"] = InstrumentId.from_str(config["instrument_id"])
    strategy_config = MyNSEStrategyConfig(**config)

    # Add strategy
    strategy = MyNSEStrategy(config=strategy_config)
    engine.add_strategy(strategy)

    # Run backtest
    engine.run()

    # Get results
    result = engine.get_result()

    print("=" * 80)
    print("DEBUGGING FILLS REPORT")
    print("=" * 80)

    # Generate fills report
    fills_report = engine.trader.generate_order_fills_report()

    print(f"Fills report type: {type(fills_report)}")
    print(f"Fills report shape: {fills_report.shape}")
    print(f"Fills report columns: {list(fills_report.columns)}")
    print(f"Fills report empty: {fills_report.empty}")

    if not fills_report.empty:
        print("\nFirst few rows of fills report:")
        print(fills_report.head())

        print("\nColumn info:")
        for col in fills_report.columns:
            print(f"  {col}: {fills_report[col].dtype}")
            if fills_report[col].dtype == "object":
                print(f"    Sample values: {fills_report[col].head(3).tolist()}")

    # Also check positions report
    positions_report = engine.trader.generate_positions_report()

    print(f"\nPositions report type: {type(positions_report)}")
    print(f"Positions report shape: {positions_report.shape}")
    print(f"Positions report columns: {list(positions_report.columns)}")
    print(f"Positions report empty: {positions_report.empty}")

    if not positions_report.empty:
        print("\nFirst few rows of positions report:")
        print(positions_report.head())

    # Check what's in the result object
    print(f"\nResult stats_pnls: {result.stats_pnls}")
    print(f"Result total_orders: {result.total_orders}")
    print(f"Result total_positions: {result.total_positions}")


if __name__ == "__main__":
    debug_fills_report()
