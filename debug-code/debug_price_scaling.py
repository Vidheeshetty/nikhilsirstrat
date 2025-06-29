import pandas as pd
import struct
from nautilus_trader.model.objects import Price

print("=== Price Scaling Debug ===\n")

# Test 1: Check how Price.from_str works
print("1. TESTING Price.from_str:")
test_price = Price.from_str("95.00")
print(f"   Price.from_str('95.00'): {test_price}")
print(f"   Raw value: {test_price.raw}")
print(f"   Precision: {test_price.precision}")
print(f"   As double: {test_price.as_double()}")

# Test 2: Check how Price constructor works
print("\n2. TESTING Price constructor:")
test_price2 = Price(9500, 2)  # value=9500, precision=2
print(f"   Price(9500, 2): {test_price2}")
print(f"   Raw value: {test_price2.raw}")
print(f"   Precision: {test_price2.precision}")
print(f"   As double: {test_price2.as_double()}")

# Test 3: Check the actual bytes in the Parquet file
print("\n3. ANALYZING PARQUET BYTES:")
parquet_file = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
df = pd.read_parquet(parquet_file)

first_bid_bytes = df.iloc[0]["bid_price"]
first_ask_bytes = df.iloc[0]["ask_price"]

print(f"   First bid bytes: {first_bid_bytes}")
print(f"   First ask bytes: {first_ask_bytes}")
print(f"   Bid bytes length: {len(first_bid_bytes)}")
print(f"   Ask bytes length: {len(first_ask_bytes)}")

# Try different decoding approaches
print("\n4. TRYING DIFFERENT DECODING APPROACHES:")

# Approach 1: Current approach (8 bytes value, 1 byte precision)
if len(first_bid_bytes) >= 9:
    value1 = struct.unpack("<q", first_bid_bytes[:8])[0]
    precision1 = first_bid_bytes[8]
    decoded1 = value1 / (10**precision1)
    print(
        f"   Approach 1 (8+1): value={value1}, precision={precision1}, decoded={decoded1}"
    )

# Approach 2: Try 4 bytes value, 1 byte precision
if len(first_bid_bytes) >= 5:
    value2 = struct.unpack("<i", first_bid_bytes[:4])[0]
    precision2 = first_bid_bytes[4]
    decoded2 = value2 / (10**precision2)
    print(
        f"   Approach 2 (4+1): value={value2}, precision={precision2}, decoded={decoded2}"
    )

# Approach 3: Try 8 bytes as double
if len(first_bid_bytes) >= 8:
    value3 = struct.unpack("<d", first_bid_bytes[:8])[0]
    print(f"   Approach 3 (8 as double): value={value3}")

# Approach 4: Try 4 bytes as float
if len(first_bid_bytes) >= 4:
    value4 = struct.unpack("<f", first_bid_bytes[:4])[0]
    print(f"   Approach 4 (4 as float): value={value4}")

# Approach 5: Check if it's a different byte order
if len(first_bid_bytes) >= 9:
    value5 = struct.unpack(">q", first_bid_bytes[:8])[0]  # big-endian
    precision5 = first_bid_bytes[8]
    decoded5 = value5 / (10**precision5)
    print(
        f"   Approach 5 (big-endian): value={value5}, precision={precision5}, decoded={decoded5}"
    )

print("\n5. COMPARING WITH ORIGINAL CSV:")
# Read the original CSV to compare
csv_file = "data/options/nse/nifty/NIFTY_2025-06-19.csv"
csv_df = pd.read_csv(csv_file)
target_symbol = "NIFTY.NSE.OPT.31Jul2025.26000.CALL"
csv_filtered = csv_df[csv_df["symbol"] == target_symbol]

print(f"   CSV data for {target_symbol}:")
print(csv_filtered[["timestamp", "bid", "ask"]].head())

print("\n6. CONCLUSION:")
print(
    "   The issue is likely in how the Price objects are being created in the conversion script."
)
print("   We need to check if the value is being multiplied by the wrong factor.")
