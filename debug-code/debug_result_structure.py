#!/usr/bin/env python3
"""
Debug script to examine the exact structure of BacktestResult object
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directories to Python path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

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
from nautilus_trader.model.objects import Money, Price, Quantity
from strategies.my_nse_strategy.strategy import MyNSEStrategy
from strategies.my_nse_strategy.config import MyNSEStrategyConfig
from nautilus_trader.backtest.results import BacktestResult


def debug_result_structure():
    """Run a backtest and examine the result object structure in detail."""

    # Configuration
    instrument_id = "NIFTY.OPT.03Jul2025.22800.CALL.NSE"
    start_time = "2025-06-18T15:18:47"
    end_time = "2025-06-20T10:00:02"

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
        instrument_ids=[instrument_id],
        as_nautilus=True,
    )
    engine.add_instrument(instruments[0])

    # Add data
    data = catalog.quote_ticks(
        instrument_ids=[instrument_id],
        start=start_time,
        end=end_time,
        as_nautilus=True,
    )
    engine.add_data(data)

    # Add strategy
    config = {
        "instrument_id": InstrumentId.from_str(instrument_id),
        "entry_buffer_pct": 0.1,
        "min_iv": 0,
        "min_oi_change": 0,
    }
    strategy_config = MyNSEStrategyConfig(**config)
    strategy = MyNSEStrategy(config=strategy_config)
    engine.add_strategy(strategy)

    # Run backtest
    engine.run()

    # Get results
    result = engine.get_result()

    print("=" * 80)
    print("DEBUG: RESULT OBJECT STRUCTURE")
    print("=" * 80)

    # Examine the result object type and attributes
    print(f"Result type: {type(result)}")
    print(f"Result class: {result.__class__}")
    print(f"Result module: {result.__module__}")
    print()

    # List all attributes
    print("All attributes:")
    for attr in dir(result):
        if not attr.startswith("_"):
            print(f"  {attr}")
    print()

    # Examine __dict__ if available
    if hasattr(result, "__dict__"):
        print("Result __dict__:")
        for key, value in result.__dict__.items():
            print(f"  {key}: {type(value)} = {value}")
        print()

    # Examine stats_pnls specifically
    print("=" * 80)
    print("DEBUG: stats_pnls STRUCTURE")
    print("=" * 80)

    print(f"stats_pnls type: {type(result.stats_pnls)}")
    print(f"stats_pnls content: {result.stats_pnls}")
    print()

    if hasattr(result.stats_pnls, "__dict__"):
        print("stats_pnls __dict__:")
        for key, value in result.stats_pnls.__dict__.items():
            print(f"  {key}: {type(value)} = {value}")
        print()

    # If it's a dict, examine each key-value pair
    if isinstance(result.stats_pnls, dict):
        print("stats_pnls dictionary contents:")
        for currency, stats in result.stats_pnls.items():
            print(f"  Currency: {currency} (type: {type(currency)})")
            print(f"  Stats type: {type(stats)}")
            print(f"  Stats content: {stats}")
            print()

            if isinstance(stats, dict):
                print(f"  Stats dictionary keys:")
                for key, value in stats.items():
                    print(f"    '{key}' (type: {type(key)}): {type(value)} = {value}")
                    # Check if it's a numpy type
                    if hasattr(value, "item"):
                        print(f"      numpy.item(): {value.item()}")
                    if hasattr(value, "dtype"):
                        print(f"      numpy.dtype: {value.dtype}")
                print()

    # Try to access PnL data directly
    print("=" * 80)
    print("DEBUG: DIRECT PnL ACCESS")
    print("=" * 80)

    try:
        # Try different ways to access PnL
        print("Attempting to access PnL data:")

        # Method 1: Direct access
        if hasattr(result, "stats_pnls") and result.stats_pnls:
            print("Method 1 - Direct stats_pnls access:")
            print(f"  result.stats_pnls: {result.stats_pnls}")

            # Try to get INR currency
            if "INR" in result.stats_pnls:
                inr_stats = result.stats_pnls["INR"]
                print(f"  INR stats: {inr_stats}")

                # Try different key formats
                possible_keys = [
                    "PnL (total)",
                    "PnL(total)",
                    "PnL_total",
                    "total_pnl",
                    "total_pnl",
                    "PnL",
                    "pnl",
                ]

                for key in possible_keys:
                    if key in inr_stats:
                        value = inr_stats[key]
                        print(f"    Found key '{key}': {value} (type: {type(value)})")
                        if hasattr(value, "item"):
                            print(f"      numpy.item(): {value.item()}")
                    else:
                        print(f"    Key '{key}' not found")

        # Method 2: Check if there are other PnL attributes
        print("\nMethod 2 - Check for other PnL attributes:")
        for attr in dir(result):
            if "pnl" in attr.lower() or "pnl" in attr.lower():
                try:
                    value = getattr(result, attr)
                    print(f"  {attr}: {value} (type: {type(value)})")
                except Exception as e:
                    print(f"  {attr}: Error accessing - {e}")

        # Method 3: Check if there are methods to get PnL
        print("\nMethod 3 - Check for PnL methods:")
        for attr in dir(result):
            if callable(getattr(result, attr)) and (
                "pnl" in attr.lower() or "pnl" in attr.lower()
            ):
                try:
                    method = getattr(result, attr)
                    if method.__code__.co_argcount == 1:  # No arguments except self
                        value = method()
                        print(f"  {attr}(): {value} (type: {type(value)})")
                except Exception as e:
                    print(f"  {attr}(): Error calling - {e}")

    except Exception as e:
        print(f"Error accessing PnL data: {e}")

    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


def debug_backtest_result(result: BacktestResult):
    print("\n=== DEBUG: BacktestResult Attributes ===")
    for attr in dir(result):
        if not attr.startswith("_"):
            try:
                value = getattr(result, attr)
                print(f"{attr}: {value}")
            except Exception as e:
                print(f"{attr}: <error: {e}>")
    print("=== END DEBUG ===\n")


if __name__ == "__main__":
    # You would import or create a BacktestResult here
    # For now, just print a message
    print("Run this script after a backtest to inspect BacktestResult attributes.")
