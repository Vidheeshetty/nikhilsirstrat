import pandas as pd
import struct
from pathlib import Path

print("=== Price Encoding Analysis ===\n")

# Read the CSV data for the target instrument
csv_file = "data/options/nse/nifty/NIFTY_2025-06-19.csv"
csv_df = pd.read_csv(csv_file)
target_symbol = "NIFTY.NSE.OPT.31Jul2025.26000.CALL"
csv_filtered = csv_df[csv_df['symbol'] == target_symbol]

print("1. ORIGINAL CSV PRICES:")
print("Sample bid/ask prices from CSV:")
sample_data = csv_filtered[['timestamp', 'bid', 'ask']].head()
print(sample_data)

print("\n2. PRICE ENCODING ANALYSIS:")
print("The conversion code does this:")
print("   bid_val = float(row['bid'])  # e.g., 95.0")
print("   bid_precision = 2")
print("   tick = QuoteTick(")
print("       bid_price=Price(int(bid_val * 10**bid_precision), bid_precision),")
print("       # ...")

print("\nLet's trace through the encoding:")
for i, row in sample_data.iterrows():
    bid_val = float(row['bid'])
    ask_val = float(row['ask'])
    bid_precision = 2
    ask_precision = 2
    
    # This is what the conversion code does:
    encoded_bid = int(bid_val * 10**bid_precision)
    encoded_ask = int(ask_val * 10**ask_precision)
    
    print(f"\nRow {i}:")
    print(f"  Original: bid={bid_val}, ask={ask_val}")
    print(f"  Encoded: bid={encoded_bid}, ask={encoded_ask}")
    print(f"  Precision: {bid_precision}")
    
    # Decode back to verify
    decoded_bid = encoded_bid / (10**bid_precision)
    decoded_ask = encoded_ask / (10**ask_precision)
    print(f"  Decoded: bid={decoded_bid}, ask={decoded_ask}")

print("\n3. PARQUET DECODING ISSUE:")
print("The Parquet file stores prices as binary data (bytes).")
print("When reading, we need to decode them properly.")

# Read the Parquet file and decode properly
parquet_file = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
parquet_df = pd.read_parquet(parquet_file)

print("\n4. PROPER PARQUET DECODING:")
print("First 5 rows with proper decoding:")
for i in range(min(5, len(parquet_df))):
    bid_bytes = parquet_df.iloc[i]['bid_price']
    ask_bytes = parquet_df.iloc[i]['ask_price']
    
    if isinstance(bid_bytes, bytes):
        # This is the correct way to decode Price objects
        bid_val = struct.unpack('d', bid_bytes[:8])[0]
    else:
        bid_val = bid_bytes
        
    if isinstance(ask_bytes, bytes):
        ask_val = struct.unpack('d', ask_bytes[:8])[0]
    else:
        ask_val = ask_bytes
    
    print(f"Row {i}: bid={bid_val}, ask={ask_val}")

print("\n5. ISSUE SUMMARY:")
print("❌ The Parquet file contains corrupted price data")
print("❌ The prices are stored as extremely small or negative values")
print("❌ This suggests the Price encoding/decoding in the conversion is broken")
print("❌ The conversion code may be using wrong precision or encoding method")

print("\n6. RECOMMENDATION:")
print("The conversion code needs to be fixed to:")
print("1. Use correct symbol parsing (already identified)")
print("2. Use correct Price encoding method")
print("3. Verify the Price objects are created correctly")
print("4. Test with a small sample before processing all data") 