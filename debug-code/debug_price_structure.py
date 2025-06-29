import pandas as pd
import struct
from nautilus_trader.model.objects import Price

print("=== Price Structure Analysis ===\n")

# Test 1: Create a Price object and see its serialization
print("1. CREATING TEST PRICE OBJECT:")
test_price = Price.from_str("95.00")
print(f"   Price.from_str('95.00'): {test_price}")
print(f"   Raw value: {test_price.raw}")
print(f"   Precision: {test_price.precision}")

# Test 2: Check if we can serialize/deserialize it
print("\n2. TESTING SERIALIZATION:")
try:
    # Try to get the bytes representation
    import pickle

    pickled = pickle.dumps(test_price)
    print(f"   Pickled length: {len(pickled)}")
    print(f"   Pickled bytes: {pickled[:20]}...")
except Exception as e:
    print(f"   Pickle error: {e}")

# Test 3: Analyze the actual 16-byte structure
print("\n3. ANALYZING 16-BYTE STRUCTURE:")
parquet_file = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
df = pd.read_parquet(parquet_file)

first_bid_bytes = df.iloc[0]["bid_price"]
print(f"   Bid bytes: {first_bid_bytes}")
print(f"   Bid bytes hex: {first_bid_bytes.hex()}")

# Try different 16-byte interpretations
print("\n4. TRYING 16-BYTE DECODING:")

# Approach 1: 8 bytes value + 8 bytes precision (or other data)
if len(first_bid_bytes) >= 16:
    value1 = struct.unpack("<q", first_bid_bytes[:8])[0]
    value2 = struct.unpack("<q", first_bid_bytes[8:16])[0]
    print(f"   Approach 1: first 8 bytes = {value1}, second 8 bytes = {value2}")

# Approach 2: 8 bytes value + 4 bytes precision + 4 bytes padding
if len(first_bid_bytes) >= 16:
    value1 = struct.unpack("<q", first_bid_bytes[:8])[0]
    precision1 = struct.unpack("<i", first_bid_bytes[8:12])[0]
    padding1 = struct.unpack("<i", first_bid_bytes[12:16])[0]
    print(f"   Approach 2: value={value1}, precision={precision1}, padding={padding1}")

# Approach 3: 8 bytes value + 1 byte precision + 7 bytes padding
if len(first_bid_bytes) >= 16:
    value1 = struct.unpack("<q", first_bid_bytes[:8])[0]
    precision1 = first_bid_bytes[8]
    print(f"   Approach 3: value={value1}, precision={precision1}")

# Approach 4: Check if it's a different structure entirely
print(
    f"   Approach 4: All 16 bytes as 8 doubles: {struct.unpack('<dd', first_bid_bytes)}"
)

# Test 5: Check if the issue is in the conversion script
print("\n5. CHECKING CONVERSION SCRIPT ISSUE:")
print(
    "   The issue might be that Price.from_str() is creating the wrong internal representation."
)
print("   Let's check what happens when we create Price objects manually:")

# Test manual Price creation
manual_price = Price(9500, 2)  # value=9500, precision=2
print(f"   Manual Price(9500, 2): {manual_price}")
print(f"   Manual raw value: {manual_price.raw}")
print(f"   Manual precision: {manual_price.precision}")

# The issue might be that Price.from_str() is using a different scale
print("\n6. CONCLUSION:")
print("   The Price.from_str() method seems to be using a different internal scale.")
print("   We should use Price(value, precision) constructor instead.")
print("   Let's fix the conversion script to use the correct approach.")
