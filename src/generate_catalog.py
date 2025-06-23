import os
import pandas as pd
from datetime import datetime

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

# --- Set directories
csv_dir = "data/nse"
catalog_dir = "catalog"
catalog_meta_dir = "catalog-meta"
os.makedirs(catalog_dir, exist_ok=True)
os.makedirs(catalog_meta_dir, exist_ok=True)

# --- Initialize Parquet catalog to store core data (quote ticks and instruments)
catalog = ParquetDataCatalog(catalog_dir)

# --- Storage lists
all_ticks = []                 # Stores QuoteTick instances
instrument_ids = set()         # Keeps track of all unique instrument IDs
meta_records = []              # Stores auxiliary/meta data as dict rows

# --- Loop through each CSV file in the input directory
for fname in os.listdir(csv_dir):
    if not fname.endswith(".csv") or fname.startswith("._"):
        continue

    print(f"Reading {fname}")
    df = pd.read_csv(os.path.join(csv_dir, fname))

    # Convert timestamps to nanoseconds since epoch (UNIX time)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%m/%d/%y %H:%M")
    df["timestamp"] = df["timestamp"].apply(dt_to_unix_nanos)

    # --- Parse rows into QuoteTick objects
    for _, row in df.iterrows():
        try:
             
            iid_str = row["symbol"].strip()
            parts = iid_str.split(".")
            symbol = parts[0]               # e.g. BANKNIFTY
            venue = parts[1]                # e.g. NSE
            type = parts[2]                 # e.g. OPTION
            expiry_raw = parts[3]           # e.g. 26Jun2025
            strike = float(parts[4])
            right = parts[5].upper()        # CALL or PUT
            symbolplus = f"{symbol}.{type}.{expiry_raw}.{int(strike)}.{right}"
            instrument_id = InstrumentId(symbol=Symbol(symbolplus), venue=Venue(venue))

            # Setup price and size values
            bid_val = float(row["bid"])
            ask_val = float(row["ask"])
            bid_precision = 2
            ask_precision = 2
            bid_size_val = float(row.get("bid_size", 1))
            ask_size_val = float(row.get("ask_size", 1))
            size_precision = 0

            # Create QuoteTick object
            tick = QuoteTick(
                instrument_id=instrument_id,
                ts_event=int(row["timestamp"]),
                ts_init=int(row["timestamp"]),
                bid_price=Price(int(bid_val * 10**bid_precision), bid_precision),
                ask_price=Price(int(ask_val * 10**ask_precision), ask_precision),
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
print(list(instrument_ids)[0])
print(list(meta_records)[0])
print(all_ticks[0])
# Example loop for just 1 instrument ID
dummy_instruments = []
for iid in instrument_ids:
    try:
        print(f"🔍 Processing: {iid.value}")
        parts = iid.value.split(".")
        symbol = parts[0]               # e.g. BANKNIFTY
        type = parts[1] 
        expiry_raw = parts[2]           # e.g. 26Jun2025
        strike = float(parts[3])
        right = parts[4].upper()        # CALL or PUT
        venue = parts[5]               # e.g. NSE
        symbolplus = f"{symbol}.{type}.{expiry_raw}.{int(strike)}.{right}"

        expiry_dt = datetime.strptime(expiry_raw, "%d%b%Y")
        expiry_utc = expiry_dt.replace(hour=15, minute=30, tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)

        option = OptionContract(
            instrument_id=InstrumentId(symbol=Symbol(symbolplus ), venue=Venue(venue)),
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
catalog.write_data(all_ticks)
# --- Write meta-data (IV, OI, etc.) to separate catalog-meta folder
meta_df = pd.DataFrame(meta_records)
meta_df.to_parquet(os.path.join(catalog_meta_dir, "tick_metadata.parquet"), index=False)

print(f"\n✅ Written {len(all_ticks)} quote ticks to {catalog_dir}/")
print(f"✅ Written {len(meta_df)} metadata records to {catalog_meta_dir}/")
print(f"✅ Written {len(dummy_instruments)} dummy instruments")

# Create a DataFrame of instrument metadata
instrument_meta = [{
    "instrument_id": str(inst.id),
    "symbol": str(inst.raw_symbol),
    "strike": float(inst.strike_price.as_double()),
    "expiry": inst.expiration_ns,
    "option_kind": inst.option_kind.name,
    "venue": inst.exchange,
    "activation_ns": inst.activation_ns,
} for inst in dummy_instruments]

df_instruments = pd.DataFrame(instrument_meta)
df_instruments.to_parquet(os.path.join(catalog_meta_dir, "instruments.parquet"), index=False)

print(f"✅ Written {len(dummy_instruments)} dummy instruments to instrument metadata") 