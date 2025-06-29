import pandas as pd
import struct

print("=== Testing Fixed Price Decoding ===\n")

# Test the new Parquet file
parquet_file = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
df = pd.read_parquet(parquet_file)


def decode_price(price_bytes):
    # FIXED: Use correct decoding for Price constructor
    if isinstance(price_bytes, bytes) and len(price_bytes) >= 9:
        value = struct.unpack("<q", price_bytes[:8])[0]
        precision = price_bytes[8]
        return value / (10**precision)
    return None


print("First 10 decoded prices from FIXED Parquet:")
for i in range(min(10, len(df))):
    bid = decode_price(df.iloc[i]["bid_price"])
    ask = decode_price(df.iloc[i]["ask_price"])
    print(f"Row {i}: bid={bid}, ask={ask}")

print("\nComparing with original CSV:")
# Read the original CSV to compare
csv_file = "data/options/nse/nifty/NIFTY_2025-06-19.csv"
csv_df = pd.read_csv(csv_file)
target_symbol = "NIFTY.NSE.OPT.31Jul2025.26000.CALL"
csv_filtered = csv_df[csv_df["symbol"] == target_symbol]

print(f"CSV data for {target_symbol} (first 10 rows):")
print(csv_filtered[["timestamp", "bid", "ask"]].head(10))
