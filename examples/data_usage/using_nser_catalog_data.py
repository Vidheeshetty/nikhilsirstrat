#!/usr/bin/env python3
"""
Example: Using NSER Catalog Data

This script demonstrates how to load and use the NSER NIFTY futures data
that has been converted to Nautilus Trader format.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog


def main():
    """Demonstrate loading and using NSER catalog data."""

    # Path to the NSER catalog data
    catalog_path = (
        "catalog-data/source=NSER/instrument=FUT/venue=NSE/symbol=NIFTY/timeframe=DAILY"
    )

    print("=== NSER NIFTY Futures Data Example ===\n")

    # Initialize catalog
    catalog = ParquetDataCatalog(catalog_path)

    # Get all available instruments
    instruments = catalog.instruments()
    print(f"Available instruments: {len(instruments)}")

    # Show first few instruments
    print("\nFirst 5 contracts:")
    for i, inst in enumerate(instruments[:5]):
        print(f"  {i + 1}. {inst.id}")

    # Get a specific contract for detailed analysis
    target_contract = "NIFTY20240125.FUT.NSE"  # January 2024 expiry

    print(f"\n=== Analyzing {target_contract} ===")

    # Get bars for this contract
    bar_type = f"{target_contract}-1-DAY-LAST-EXTERNAL"
    bars = catalog.bars(bar_types=[bar_type])

    if bars:
        print(f"Found {len(bars)} daily bars")

        # Show first and last bars
        first_bar = bars[0]
        last_bar = bars[-1]

        print("\nFirst trading day:")
        print(f"  Date: {first_bar.ts_event}")
        print(
            f"  OHLC: {float(first_bar.open):.2f}, {float(first_bar.high):.2f}, {float(first_bar.low):.2f}, {float(first_bar.close):.2f}"
        )

        print("\nLast trading day:")
        print(f"  Date: {last_bar.ts_event}")
        print(
            f"  OHLC: {float(last_bar.open):.2f}, {float(last_bar.high):.2f}, {float(last_bar.low):.2f}, {float(last_bar.close):.2f}"
        )

        # Calculate some basic statistics
        closes = [float(bar.close) for bar in bars]
        highs = [float(bar.high) for bar in bars]
        lows = [float(bar.low) for bar in bars]

        print("\nPrice Statistics:")
        print(f"  Highest: {max(highs):.2f}")
        print(f"  Lowest: {min(lows):.2f}")
        print(f"  Final close: {closes[-1]:.2f}")
        print(f"  Total return: {((closes[-1] / closes[0]) - 1) * 100:.2f}%")

        # Show how to extract prices for strategy use
        print("\n=== For Strategy Use ===")
        print("# Extract close prices as list:")
        print(f"close_prices = {closes[:5]} ... ({len(closes)} total)")

        print("\n# Access individual bar data:")
        print("for bar in bars:")
        print("    timestamp = bar.ts_event")
        print(
            "    ohlc = (float(bar.open), float(bar.high), float(bar.low), float(bar.close))"
        )
        print("    # Use in your strategy logic...")

    else:
        print("No bars found for this contract")

    print("\n=== Integration with Strategies ===")
    print("To use this data in your strategies:")
    print("1. Update your DataManager to point to this catalog path")
    print("2. Use the instrument IDs shown above")
    print("3. The data is already in Nautilus Trader format")
    print(f"4. Catalog path: {catalog_path}")


if __name__ == "__main__":
    main()
