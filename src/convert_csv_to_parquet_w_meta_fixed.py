import os
import pandas as pd
from datetime import datetime
import shutil
from pathlib import Path

# Nautilus imports for constructing data and instruments
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.instruments.option_contract import OptionContract
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import AssetClass, OptionKind
from nautilus_trader.core.datetime import dt_to_unix_nanos
from datetime import datetime, timezone

import logging

# Enable debug-level logs
logging.basicConfig(level=logging.DEBUG)

# --- Set directories (one level up from src folder)
# Get the script's directory and navigate to project root
script_dir = Path(__file__).parent
project_root = script_dir.parent
csv_dir = project_root / "data" / "options" / "nse" / "nifty"
catalog_dir = project_root / "catalog-data" / "my_nse_strategy" / "catalog"
catalog_meta_dir = project_root / "catalog-data" / "my_nse_strategy" / "catalog-meta"

print(f"📁 CSV Directory: {csv_dir}")
print(f"📁 Catalog Directory: {catalog_dir}")
print(f"📁 Meta Directory: {catalog_meta_dir}")

# Check if CSV directory exists
if not csv_dir.exists():
    print(f"❌ Error: CSV directory does not exist: {csv_dir}")
    print(f"Available directories:")
    for item in project_root.glob("data/**/*"):
        if item.is_dir():
            print(f"  - {item}")
    exit(1)

# --- Clear existing parquet folders
print("🧹 Clearing existing parquet folders...")
if catalog_dir.exists():
    shutil.rmtree(catalog_dir)
    print(f"✅ Cleared: {catalog_dir}")

if catalog_meta_dir.exists():
    shutil.rmtree(catalog_meta_dir)
    print(f"✅ Cleared: {catalog_meta_dir}")

# --- Create fresh directories
catalog_dir.mkdir(parents=True, exist_ok=True)
catalog_meta_dir.mkdir(parents=True, exist_ok=True)
print("✅ Created fresh parquet directories")

# --- Initialize Parquet catalog to store core data (quote ticks and instruments)
catalog = ParquetDataCatalog(str(catalog_dir))

# --- Storage lists
all_ticks = []                 # Stores QuoteTick instances
instrument_ids = set()         # Keeps track of all unique instrument IDs
meta_records = []              # Stores auxiliary/meta data as dict rows

# --- Loop through each CSV file in the input directory
for fname in csv_dir.glob("*.csv"):
    if fname.name.startswith("._"):
        continue

    print(f"Reading {fname.name}")
    df = pd.read_csv(fname)

    # Convert timestamps to nanoseconds since epoch (UNIX time)
    # Handle different timestamp formats
    try:
        # Try ISO format first (2025-06-19 03:00:02)
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # Try alternative ISO format (2025-06-19 03:00)
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # Try the original format (%m/%d/%y %H:%M)
                df["timestamp"] = pd.to_datetime(df["timestamp"], format="%m/%d/%y %H:%M")
            except ValueError:
                # Fallback to pandas auto-detection
                df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    df["timestamp"] = df["timestamp"].apply(dt_to_unix_nanos)

    # --- Parse rows into QuoteTick objects
    for _, row in df.iterrows():
        try:
             
            iid_str = row["symbol"].strip()
            parts = iid_str.split(".")
            
            # FIXED: Correct parsing for CSV format: NIFTY.NSE.OPT.31Jul2025.26000.CALL
            symbol = parts[0]               # e.g. NIFTY
            venue = parts[1]                # e.g. NSE
            type = parts[2]                 # e.g. OPT
            expiry_raw = parts[3]           # e.g. 31Jul2025
            strike = float(parts[4])        # e.g. 26000
            right = parts[5].upper()        # e.g. CALL
            
            # FIXED: Create correct instrument ID format: NIFTY.OPT.31Jul2025.26000.CALL.NSE
            symbolplus = f"{symbol}.{type}.{expiry_raw}.{int(strike)}.{right}"
            instrument_id = InstrumentId(symbol=Symbol(symbolplus), venue=Venue(venue))

            # Setup price and size values
            bid_val = float(row["bid"])
            ask_val = float(row["ask"])
            
            # FIXED: Use proper precision and Price.from_str method
            bid_precision = 2
            ask_precision = 2
            bid_size_val = float(row.get("bid_size", 1))
            ask_size_val = float(row.get("ask_size", 1))
            size_precision = 0

            # FIXED: Use Price.from_str instead of manual encoding
            bid_price = Price.from_str(f"{bid_val:.2f}")
            ask_price = Price.from_str(f"{ask_val:.2f}")

            # Create QuoteTick object
            tick = QuoteTick(
                instrument_id=instrument_id,
                ts_event=int(row["timestamp"]),
                ts_init=int(row["timestamp"]),
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=Quantity(int(bid_size_val * 10**size_precision), size_precision),
                ask_size=Quantity(int(ask_size_val * 10**size_precision), size_precision),
            )

            all_ticks.append(tick)
          
            instrument_ids.add(instrument_id)

            # Save the meta fields separately
            meta_records.append({
                "instrument_id": f"{symbolplus}.{venue}",
                "timestamp": row["timestamp"],
                "impliedVolatility": row.get("impliedVolatility"),
                "openInterest": row.get("openInterest"),
                "last": row.get("last"),
                "pChange": row.get("pChange"),
            })

        except Exception as e:
            print(f"⚠️ Skipping row due to tick parsing error: {e}")

# --- Build dummy instruments using OptionContract.from_dict
# This will store instrument metadata needed by the engine
print(f"Processing {len(instrument_ids)} unique instruments...")
dummy_instruments = []
for iid in instrument_ids:
    try:
        print(f"🔍 Processing: {iid.value}")
        parts = iid.value.split(".")
        symbol = parts[0]               # e.g. NIFTY
        type = parts[1] 
        expiry_raw = parts[2]           # e.g. 31Jul2025
        strike = float(parts[3])
        right = parts[4].upper()        # e.g. CALL
        venue = parts[5]               # e.g. NSE
        symbolplus = f"{symbol}.{type}.{expiry_raw}.{int(strike)}.{right}"

        expiry_dt = datetime.strptime(expiry_raw, "%d%b%Y")
        expiry_utc = expiry_dt.replace(hour=15, minute=30, tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)

        option = OptionContract(
            instrument_id=InstrumentId(symbol=Symbol(symbolplus), venue=Venue(venue)),
            raw_symbol=Symbol(symbol),
            asset_class=AssetClass.INDEX,     # Same as example
            exchange=venue,
            currency=Currency.from_str("INR"),
            price_precision=2,
            price_increment=Price.from_str("0.05"),
            multiplier=Quantity.from_int(15),
            lot_size=Quantity.from_int(1),
            underlying=f"{symbol}.{venue}.INDEX",
            option_kind=OptionKind[right],
            strike_price=Price.from_str(str(strike)),
            activation_ns=0,  # Set to 0 to make it always active
            expiration_ns=dt_to_unix_nanos(expiry_utc),
            ts_event=dt_to_unix_nanos(now_utc),
            ts_init=dt_to_unix_nanos(now_utc),
        )

        print(f"✅ Created OptionContract: {option.id}")
        dummy_instruments.append(option)
    except Exception as e:
        print(f"⚠️ Skipping {iid.value} due to instrument creation error: {e}")

catalog.write_data(dummy_instruments)

# Sort ticks by timestamp before writing
print("📊 Sorting quote ticks by timestamp...")
all_ticks.sort(key=lambda x: x.ts_init)
print(f"✅ Sorted {len(all_ticks)} quote ticks")

catalog.write_data(all_ticks)

# --- Write meta-data (IV, OI, etc.) to separate catalog-meta folder
meta_df = pd.DataFrame(meta_records)
meta_df.to_parquet(catalog_meta_dir / "tick_metadata.parquet", index=False)

print(f"\n✅ Written {len(all_ticks)} quote ticks to {catalog_dir}/")
print(f"✅ Written {len(meta_df)} metadata records to {catalog_meta_dir}/")
print(f"✅ Written {len(dummy_instruments)} dummy instruments")

# Create a DataFrame of instrument metadata
instrument_meta = [{
    "instrument_id": str(inst.id),
    "symbol": str(inst.raw_symbol),
    "strike": float(inst.strike_price.as_double()),  # Fixed: use as_double() method from Price object
    "expiry": inst.expiration_ns,
    "option_kind": inst.option_kind.name,
    "venue": inst.exchange,
    "activation_ns": inst.activation_ns,
} for inst in dummy_instruments]

df_instruments = pd.DataFrame(instrument_meta)
df_instruments.to_parquet(catalog_meta_dir / "instruments.parquet", index=False)

print(f"✅ Written {len(dummy_instruments)} dummy instruments to instrument metadata")

# --- Test the conversion with a sample
print("\n🧪 TESTING CONVERSION:")
test_instrument = "NIFTY.OPT.31Jul2025.26000.CALL.NSE"
test_file = catalog_dir / "data" / "quote_tick" / test_instrument / "part-0.parquet"

if test_file.exists():
    print(f"✅ Test file created: {test_file}")
    test_df = pd.read_parquet(test_file)
    print(f"   Shape: {test_df.shape}")
    print(f"   Columns: {test_df.columns.tolist()}")
    
    # Test price decoding
    if len(test_df) > 0:
        first_row = test_df.iloc[0]
        print(f"   First row bid_price type: {type(first_row['bid_price'])}")
        print(f"   First row ask_price type: {type(first_row['ask_price'])}")
        
        # Try to decode the first price
        try:
            import struct
            if isinstance(first_row['bid_price'], bytes):
                bid_val = struct.unpack('d', first_row['bid_price'][:8])[0]
                print(f"   Decoded bid: {bid_val}")
            else:
                print(f"   Bid price: {first_row['bid_price']}")
        except Exception as e:
            print(f"   Error decoding bid: {e}")
else:
    print(f"❌ Test file not found: {test_file}") 