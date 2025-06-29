#!/usr/bin/env python3
"""
Investigate actual trade data for NIFTY.OPT.03Jul2025.22800.CALL.NSE
"""

import sys
import os
from pathlib import Path
import pandas as pd
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import QuoteTick

# Add parent directories to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

# Instrument to investigate
instrument_id = "NIFTY.OPT.03Jul2025.22800.CALL.NSE"

print(f"Investigating trade data for: {instrument_id}")
print("=" * 80)

# 1. Check CSV data first
print("1. CSV DATA ANALYSIS")
print("-" * 40)

csv_files = [
    ("2025-06-18", "data/options/nse/nifty/NIFTY_2025-06-18.csv"),
    ("2025-06-19", "data/options/nse/nifty/NIFTY_2025-06-19.csv"),
    ("2025-06-20", "data/options/nse/nifty/NIFTY_2025-06-20.csv"),
]

# The CSV symbol format is different from the instrument_id
csv_symbol = "NIFTY.NSE.OPT.03Jul2025.22800.CALL"

print(f"Looking for CSV symbol: {csv_symbol}")

for date, csv_file in csv_files:
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        df_instrument = df[df["symbol"] == csv_symbol]

        if len(df_instrument) > 0:
            print(f"\n{date}: Found {len(df_instrument)} rows")
            print("Sample data:")
            print(df_instrument[["timestamp", "bid", "ask", "last", "volume"]].head(3))
            print(
                f"Price range: bid={df_instrument['bid'].min():.2f}-{df_instrument['bid'].max():.2f}, ask={df_instrument['ask'].min():.2f}-{df_instrument['ask'].max():.2f}"
            )
        else:
            print(f"\n{date}: No data found")
    else:
        print(f"\n{date}: CSV file not found")

# 2. Check Parquet data
print("\n" + "=" * 80)
print("2. PARQUET DATA ANALYSIS")
print("-" * 40)

catalog_dir = "catalog-data/my_nse_strategy/catalog"
if os.path.exists(catalog_dir):
    catalog = ParquetDataCatalog(catalog_dir)

    try:
        ticks = catalog.query(data_cls=QuoteTick, identifiers=[instrument_id])

        if len(ticks) > 0:
            print(f"Found {len(ticks)} quote ticks in Parquet")

            # Convert to DataFrame for easier analysis
            tick_data = []
            for tick in ticks:
                tick_data.append(
                    {
                        "timestamp": tick.ts_init,
                        "bid": float(tick.bid_price),
                        "ask": float(tick.ask_price),
                        "bid_size": float(tick.bid_size),
                        "ask_size": float(tick.ask_size),
                    }
                )

            df_ticks = pd.DataFrame(tick_data)
            df_ticks["timestamp"] = pd.to_datetime(df_ticks["timestamp"], unit="ns")

            print(
                f"Data range: {df_ticks['timestamp'].min()} to {df_ticks['timestamp'].max()}"
            )
            print(f"Total ticks: {len(df_ticks)}")

            # Check for zero prices
            zero_bids = (df_ticks["bid"] == 0).sum()
            zero_asks = (df_ticks["ask"] == 0).sum()
            print(f"Zero bids: {zero_bids} ({zero_bids / len(df_ticks) * 100:.1f}%)")
            print(f"Zero asks: {zero_asks} ({zero_asks / len(df_ticks) * 100:.1f}%)")

            # Show first and last few valid prices
            valid_ticks = df_ticks[(df_ticks["bid"] > 0) & (df_ticks["ask"] > 0)]
            if len(valid_ticks) > 0:
                print(f"\nFirst 5 valid prices:")
                print(valid_ticks[["timestamp", "bid", "ask"]].head())

                print(f"\nLast 5 valid prices:")
                print(valid_ticks[["timestamp", "bid", "ask"]].tail())

                # Calculate mid prices
                valid_ticks["mid"] = (valid_ticks["bid"] + valid_ticks["ask"]) / 2
                print(f"\nPrice statistics (valid prices only):")
                print(
                    f"Bid range: {valid_ticks['bid'].min():.2f} - {valid_ticks['bid'].max():.2f}"
                )
                print(
                    f"Ask range: {valid_ticks['ask'].min():.2f} - {valid_ticks['ask'].max():.2f}"
                )
                print(
                    f"Mid range: {valid_ticks['mid'].min():.2f} - {valid_ticks['mid'].max():.2f}"
                )

                # Last valid price (this is what the backtest uses for unrealized PnL)
                last_valid = valid_ticks.iloc[-1]
                print(f"\nLast valid price (used for unrealized PnL):")
                print(f"Timestamp: {last_valid['timestamp']}")
                print(f"Bid: {last_valid['bid']:.2f}")
                print(f"Ask: {last_valid['ask']:.2f}")
                print(f"Mid: {last_valid['mid']:.2f}")
            else:
                print("No valid prices found in Parquet data!")

        else:
            print("No quote ticks found in Parquet data")

    except Exception as e:
        print(f"Error querying Parquet data: {e}")
else:
    print(f"Catalog directory not found: {catalog_dir}")

# 3. Check the actual backtest log for this instrument
print("\n" + "=" * 80)
print("3. BACKTEST LOG ANALYSIS")
print("-" * 40)

log_file = "_summary.txts/2025-06-22/21-32-21-backtest-NIFTY.OPT.03Jul2025.22800.CALL.NSE_summary.txt"
if os.path.exists(log_file):
    print(f"Found backtest summary: {log_file}")
    with open(log_file, "r") as f:
        content = f.read()
        print(content)
else:
    print(f"Backtest summary not found: {log_file}")

print("\n" + "=" * 80)
print("INVESTIGATION COMPLETE")
print("=" * 80)
