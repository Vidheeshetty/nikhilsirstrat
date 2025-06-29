import pandas as pd
import struct
from nautilus_trader.model.objects import Price

print("=== Detailed Byte Structure Analysis ===\n")

# Test 1: Create a Price object and examine its structure
print("1. CREATING TEST PRICE OBJECTS:")
test_price1 = Price(9500, 2)  # 95.00
test_price2 = Price(9505, 2)  # 95.05

print(f"   Price(9500, 2): {test_price1}")
print(f"   Price(9505, 2): {test_price2}")

# Test 2: Check if we can get the raw bytes
print("\n2. CHECKING RAW BYTES:")
try:
    # Try to get the raw bytes representation
    import pickle

    pickled1 = pickle.dumps(test_price1)
    print(f"   Pickled Price(9500, 2) length: {len(pickled1)}")
    print(f"   Pickled bytes: {pickled1[:50]}...")
except Exception as e:
    print(f"   Pickle error: {e}")

# Test 3: Analyze the actual Parquet bytes
print("\n3. ANALYZING PARQUET BYTES:")
parquet_file = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
df = pd.read_parquet(parquet_file)

first_bid_bytes = df.iloc[0]["bid_price"]
first_ask_bytes = df.iloc[0]["ask_price"]

print(f"   Bid bytes: {first_bid_bytes}")
print(f"   Bid bytes hex: {first_bid_bytes.hex()}")
print(f"   Ask bytes: {first_ask_bytes}")
print(f"   Ask bytes hex: {first_ask_bytes.hex()}")

# Test 4: Try different byte interpretations
print("\n4. TRYING DIFFERENT BYTE INTERPRETATIONS:")

# Check if it's a different structure
if len(first_bid_bytes) >= 16:
    # Try as 16 bytes with different interpretations
    print(f"   As 2 int64s: {struct.unpack('<qq', first_bid_bytes)}")
    print(f"   As 4 int32s: {struct.unpack('<iiii', first_bid_bytes)}")
    print(f"   As 2 doubles: {struct.unpack('<dd', first_bid_bytes)}")
    print(f"   As 4 floats: {struct.unpack('<ffff', first_bid_bytes)}")

# Test 5: Check if the issue is in the Price constructor
print("\n5. CHECKING PRICE CONSTRUCTOR:")
print("   The issue might be that the Price constructor is not working as expected.")
print("   Let's try a different approach:")

# Test 6: Try using Price.from_str with different formats
print("\n6. TESTING Price.from_str:")
try:
    test_price3 = Price.from_str("95.00")
    test_price4 = Price.from_str("95.05")
    print(f"   Price.from_str('95.00'): {test_price3}")
    print(f"   Price.from_str('95.05'): {test_price4}")
    print(f"   Raw values: {test_price3.raw}, {test_price4.raw}")
    print(f"   Precisions: {test_price3.precision}, {test_price4.precision}")
except Exception as e:
    print(f"   Error: {e}")

print("\n7. CONCLUSION:")
print("   The Price objects seem to have a complex internal structure.")
print("   We need to understand how Nautilus serializes Price objects to Parquet.")
print("   The issue might be that we need to use Nautilus's own serialization methods.")
