import pandas as pd
import struct
from pathlib import Path

print("=== CSV to Parquet Conversion Analysis ===\n")

# 1. Check original CSV data
csv_file = "data/options/nse/nifty/NIFTY_2025-06-19.csv"
print("1. ORIGINAL CSV DATA:")
print(f"Reading: {csv_file}")
csv_df = pd.read_csv(csv_file)
print(f"CSV shape: {csv_df.shape}")
print(f"CSV columns: {csv_df.columns.tolist()}")

# Check for NIFTY.OPT.31Jul2025.26000.CALL.NSE data in CSV
target_symbol = "NIFTY.NSE.OPT.31Jul2025.26000.CALL"
csv_filtered = csv_df[csv_df["symbol"] == target_symbol]
print(f"\nFound {len(csv_filtered)} rows for {target_symbol} in CSV")
if len(csv_filtered) > 0:
    print("Sample CSV data:")
    print(csv_filtered[["timestamp", "symbol", "bid", "ask", "last"]].head())
    print("\nBid/Ask ranges in CSV:")
    print(f"Bid range: {csv_filtered['bid'].min()} to {csv_filtered['bid'].max()}")
    print(f"Ask range: {csv_filtered['ask'].min()} to {csv_filtered['ask'].max()}")
else:
    print(f"❌ No data found for {target_symbol} in CSV!")
    print("Available symbols in CSV:")
    print(csv_df["symbol"].unique()[:10])  # Show first 10 unique symbols

# 2. Check generated Parquet data
parquet_file = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
print(f"\n2. GENERATED PARQUET DATA:")
print(f"Reading: {parquet_file}")
parquet_df = pd.read_parquet(parquet_file)
print(f"Parquet shape: {parquet_df.shape}")
print(f"Parquet columns: {parquet_df.columns.tolist()}")

# Decode the binary price data
print("\n3. DECODING PARQUET PRICE DATA:")
print("First 5 rows decoded:")
for i in range(min(5, len(parquet_df))):
    bid_bytes = parquet_df.iloc[i]["bid_price"]
    ask_bytes = parquet_df.iloc[i]["ask_price"]

    if isinstance(bid_bytes, bytes):
        bid_val = struct.unpack("d", bid_bytes[:8])[0]
    else:
        bid_val = bid_bytes

    if isinstance(ask_bytes, bytes):
        ask_val = struct.unpack("d", ask_bytes[:8])[0]
    else:
        ask_val = ask_bytes

    print(f"Row {i}: bid={bid_val}, ask={ask_val}")

print("\nLast 5 rows decoded:")
for i in range(max(0, len(parquet_df) - 5), len(parquet_df)):
    bid_bytes = parquet_df.iloc[i]["bid_price"]
    ask_bytes = parquet_df.iloc[i]["ask_price"]

    if isinstance(bid_bytes, bytes):
        bid_val = struct.unpack("d", bid_bytes[:8])[0]
    else:
        bid_val = bid_bytes

    if isinstance(ask_bytes, bytes):
        ask_val = struct.unpack("d", ask_bytes[:8])[0]
    else:
        ask_val = ask_bytes

    print(f"Row {i}: bid={bid_val}, ask={ask_val}")

# 4. Check if the instrument exists in CSV
print(f"\n4. INSTRUMENT ANALYSIS:")
print(f"Looking for: {target_symbol}")
if len(csv_filtered) == 0:
    print(
        "❌ PROBLEM: The instrument NIFTY.OPT.31Jul2025.26000.CALL.NSE is not in the CSV!"
    )
    print("This means the Parquet file was generated with dummy/placeholder data.")

    # Check what instruments are actually in the CSV
    print("\nAvailable instruments in CSV (first 20):")
    unique_symbols = csv_df["symbol"].unique()
    for i, symbol in enumerate(unique_symbols[:20]):
        print(f"  {i + 1}. {symbol}")

    # Check for similar instruments
    print("\nLooking for similar instruments (NIFTY with 26000 strike):")
    similar = csv_df[csv_df["symbol"].str.contains("26000")]
    if len(similar) > 0:
        print("Found similar instruments:")
        print(similar["symbol"].unique())
    else:
        print("No instruments with strike 26000 found")
