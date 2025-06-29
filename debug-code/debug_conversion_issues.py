import pandas as pd
from pathlib import Path

print("=== CSV to Parquet Conversion Issues Analysis ===\n")

# Read the CSV data
csv_file = "data/options/nse/nifty/NIFTY_2025-06-19.csv"
csv_df = pd.read_csv(csv_file)

# Find the target instrument data
target_symbol = "NIFTY.NSE.OPT.31Jul2025.26000.CALL"
csv_filtered = csv_df[csv_df["symbol"] == target_symbol]

print("1. ORIGINAL CSV DATA FOR TARGET INSTRUMENT:")
print(f"Found {len(csv_filtered)} rows")
print("Sample data:")
print(csv_filtered[["timestamp", "symbol", "bid", "ask", "last"]].head())

print("\n2. SYMBOL PARSING ANALYSIS:")
# Show how the conversion code would parse this symbol
sample_row = csv_filtered.iloc[0]
iid_str = sample_row["symbol"].strip()
print(f"Original symbol: '{iid_str}'")

parts = iid_str.split(".")
print(f"Split parts: {parts}")

# This is how the conversion code parses it:
symbol = parts[0]  # e.g. NIFTY
venue = parts[1]  # e.g. NSE
type = parts[2]  # e.g. OPT
expiry_raw = parts[3]  # e.g. 31Jul2025
strike = float(parts[4])  # e.g. 26000
right = parts[5].upper()  # e.g. CALL
symbolplus = f"{symbol}.{type}.{expiry_raw}.{int(strike)}.{right}"
instrument_id = f"{symbolplus}.{venue}"

print(f"Parsed components:")
print(f"  symbol: {symbol}")
print(f"  venue: {venue}")
print(f"  type: {type}")
print(f"  expiry_raw: {expiry_raw}")
print(f"  strike: {strike}")
print(f"  right: {right}")
print(f"  symbolplus: {symbolplus}")
print(f"  final instrument_id: {instrument_id}")

print("\n3. ISSUE IDENTIFICATION:")
print("❌ PROBLEM 1: Symbol parsing mismatch")
print(f"   CSV symbol format: NIFTY.NSE.OPT.31Jul2025.26000.CALL")
print(f"   Expected format: NIFTY.OPT.31Jul2025.26000.CALL.NSE")
print(f"   The conversion code expects: symbol.type.expiry.strike.right.venue")
print(f"   But CSV has: symbol.venue.type.expiry.strike.right")

print("\n❌ PROBLEM 2: The conversion code is creating wrong instrument IDs")
print(f"   It's looking for: NIFTY.OPT.31Jul2025.26000.CALL.NSE")
print(f"   But should be looking for: NIFTY.NSE.OPT.31Jul2025.26000.CALL")

print("\n4. CORRECTED PARSING:")
print("The conversion code should parse like this:")
print("   parts = iid_str.split('.')")
print("   symbol = parts[0]        # NIFTY")
print("   venue = parts[1]         # NSE")
print("   type = parts[2]          # OPT")
print("   expiry_raw = parts[3]    # 31Jul2025")
print("   strike = float(parts[4]) # 26000")
print("   right = parts[5].upper() # CALL")
print(
    "   instrument_id = f'{symbol}.{type}.{expiry_raw}.{int(strike)}.{right}.{venue}'"
)

print("\n5. VERIFICATION:")
# Check if the corrected instrument ID exists in the catalog
corrected_id = "NIFTY.OPT.31Jul2025.26000.CALL.NSE"
print(f"Looking for corrected ID: {corrected_id}")

# Check what's actually in the catalog
catalog_dir = Path("catalog-data/my_nse_strategy/catalog/data/quote_tick")
if catalog_dir.exists():
    available_instruments = [d.name for d in catalog_dir.iterdir() if d.is_dir()]
    print(f"Available instruments in catalog: {len(available_instruments)}")
    if corrected_id in available_instruments:
        print(f"✅ Found {corrected_id} in catalog")
    else:
        print(f"❌ {corrected_id} not found in catalog")
        print("Available instruments (first 10):")
        for inst in available_instruments[:10]:
            print(f"  - {inst}")
else:
    print("❌ Catalog directory not found")
