# convert_csv_to_parquet_w_meta_fixed_v5.py

import os
import pandas as pd
from datetime import datetime, timezone
import shutil
from pathlib import Path
import logging

# Nautilus Trader imports
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.model.enums import AssetClass, OptionKind
from nautilus_trader.model.instruments.option_contract import OptionContract
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

# Enable debug-level logging
logging.basicConfig(level=logging.DEBUG)

# --- Set up directories ---
script_dir = Path(__file__).parent
project_root = script_dir.parent
csv_dir = project_root / "data" / "options" / "nse" / "nifty"
catalog_dir = project_root / "catalog-data" / "my_nse_strategy" / "catalog"
catalog_meta_dir = project_root / "catalog-data" / "my_nse_strategy" / "catalog-meta"

print(f"📁 CSV Directory: {csv_dir}")
print(f"📁 Catalog Directory: {catalog_dir}")
print(f"📁 Meta Directory: {catalog_meta_dir}")

# Check for input directory
if not csv_dir.exists():
    print(f"❌ Error: CSV directory does not exist: {csv_dir}")
    exit(1)

# Clear previous output
print("🧹 Clearing existing parquet folders...")
shutil.rmtree(catalog_dir, ignore_errors=True)
shutil.rmtree(catalog_meta_dir, ignore_errors=True)
catalog_dir.mkdir(parents=True, exist_ok=True)
catalog_meta_dir.mkdir(parents=True, exist_ok=True)

# Initialize catalog
catalog = ParquetDataCatalog(str(catalog_dir))

# Storage
all_ticks = []
instrument_ids = set()
meta_records = []

# --- Process each CSV file ---
for fname in csv_dir.glob("*.csv"):
    if fname.name.startswith("._"):
        continue

    print(f"Reading {fname.name}")
    df = pd.read_csv(fname)

    # Parse timestamp
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%y %H:%M"]:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format=fmt)
            break
        except ValueError:
            continue
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    df["timestamp"] = df["timestamp"].apply(dt_to_unix_nanos)

    # Convert rows to QuoteTicks
    for _, row in df.iterrows():
        try:
            iid_str = row["symbol"].strip()
            parts = iid_str.split(".")
            symbol = parts[0]
            venue = parts[1]
            expiry_raw = parts[3]
            strike = float(parts[4])
            right = parts[5].upper()
            symbolplus = f"{symbol}.OPT.{expiry_raw}.{int(strike)}.{right}"
            instrument_id = InstrumentId(symbol=Symbol(symbolplus), venue=Venue(venue))

            # Parse bid/ask and validate
            try:
                bid_val = float(row["bid"])
                ask_val = float(row["ask"])
            except (ValueError, TypeError):
                print(f"⚠️ Skipping non-numeric bid/ask: {row['bid']}, {row['ask']}")
                continue

            if bid_val == 0.0 or ask_val == 0.0:
                print(f"⚠️ Skipping row with zero bid/ask: bid={bid_val}, ask={ask_val}, symbol={iid_str}")
                continue

            bid_size_val = float(row.get("totalBuyQuantity", 1))
            ask_size_val = float(row.get("totalSellQuantity", 1))

            tick = QuoteTick(
                instrument_id=instrument_id,
                ts_event=int(row["timestamp"]),
                ts_init=int(row["timestamp"]),
                bid_price=Price(bid_val, 2),
                ask_price=Price(ask_val, 2),
                bid_size=Quantity(bid_size_val, 0),
                ask_size=Quantity(ask_size_val, 0),
            )

            all_ticks.append(tick)
            instrument_ids.add(instrument_id)

            meta_records.append({
                "instrument_id": f"{symbolplus}.{venue}",
                "timestamp": row["timestamp"],
                "impliedVolatility": row.get("impliedVolatility"),
                "openInterest": row.get("open_interest"),
                "last": row.get("last"),
                "pChange": row.get("pChange"),
            })

        except Exception as e:
            print(f"⚠️ Skipping row due to tick parsing error: {e}")

# --- Create dummy instruments ---
dummy_instruments = []
for iid in instrument_ids:
    try:
        parts = iid.value.split(".")
        symbol = parts[0]
        expiry_raw = parts[2]
        strike = float(parts[3])
        right = parts[4]
        venue = parts[5]

        expiry_dt = datetime.strptime(expiry_raw, "%d%b%Y")
        expiry_utc = expiry_dt.replace(hour=15, minute=30, tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)

        option = OptionContract(
            instrument_id=iid,
            raw_symbol=Symbol(symbol),
            asset_class=AssetClass.INDEX,
            exchange=venue,
            currency=Currency.from_str("INR"),
            price_precision=2,
            price_increment=Price(0.05, 2),
            multiplier=Quantity(15, 0),
            lot_size=Quantity(1, 0),
            underlying=f"{symbol}.{venue}.INDEX",
            option_kind=OptionKind[right],
            strike_price=Price(strike, 2),
            activation_ns=0,
            expiration_ns=dt_to_unix_nanos(expiry_utc),
            ts_event=dt_to_unix_nanos(now_utc),
            ts_init=dt_to_unix_nanos(now_utc),
        )

        dummy_instruments.append(option)
    except Exception as e:
        print(f"⚠️ Skipping instrument {iid.value}: {e}")

# --- Write to Parquet ---
all_ticks.sort(key=lambda x: x.ts_init)
catalog.write_data(dummy_instruments)
catalog.write_data(all_ticks)

meta_df = pd.DataFrame(meta_records)
meta_df.to_parquet(catalog_meta_dir / "tick_metadata.parquet", index=False)

# --- Write instrument metadata ---
instrument_meta = [{
    "instrument_id": str(inst.id),
    "symbol": str(inst.raw_symbol),
    "strike": float(inst.strike_price.as_double()),
    "expiry": inst.expiration_ns,
    "option_kind": inst.option_kind.name,
    "venue": inst.exchange,
    "activation_ns": inst.activation_ns,
} for inst in dummy_instruments]

pd.DataFrame(instrument_meta).to_parquet(catalog_meta_dir / "instruments.parquet", index=False)

print(f"
📄 Written {len(all_ticks)} quote ticks")
print(f"📄 Written {len(meta_df)} metadata records")
print(f"📄 Written {len(dummy_instruments)} dummy instruments")
