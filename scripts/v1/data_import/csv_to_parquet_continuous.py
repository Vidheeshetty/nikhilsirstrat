#!/usr/bin/env python3
"""CSV to Parquet converter for Continuous Futures Data.

This script handles continuous futures data without expiry dates,
creating a single synthetic continuous contract instrument.

Example:
--------
```bash
python scripts/v1/data_import/csv_to_parquet_continuous.py \
    --config config/convert_nifty_continuous_yf.yaml --clean
```
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments.futures_contract import FuturesContract
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

# Ensure repository root is importable
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.data_adapters.conversion_config import ConverterConfig

logger = logging.getLogger("csv_to_parquet_continuous")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def clear_catalog_dirs(cfg: ConverterConfig) -> None:
    """Create destination folders. If *cfg.clean* is True remove first."""
    for p in (Path(cfg.destination_catalog), Path(cfg.destination_meta)):
        if cfg.clean and p.exists():
            shutil.rmtree(p)
            logger.info("🧹 Removed %s", p)
        p.mkdir(parents=True, exist_ok=True)
        logger.info("📂 Created %s", p)


def load_continuous_csv(csv_path: str) -> pd.DataFrame:
    """Load continuous futures CSV with special date format handling.
    
    The CSV has format: date,,open,high,low,close,volume,oi
    where date is split across two columns like: 16-01-2024,00:00:00+05:30
    """
    logger.info("📖 Reading %s", csv_path)
    
    # Read raw to inspect the actual structure
    df = pd.read_csv(csv_path)
    
    # Check if we need to combine date columns (handle multiple formats)
    # Format 1: date,time,open (hourly data - separate columns)
    if 'date' in df.columns and 'time' in df.columns:
        # Combine date and time columns for hourly data
        df['DATE'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
        # Drop the original columns
        df = df.drop(['date', 'time'], axis=1)
        logger.info("✓ Detected hourly data format (date,time columns)")
    # Format 2: date,,open (daily data - split with empty column)
    elif 'date' in df.columns and len(df.columns) > 1 and df.columns[1] == 'Unnamed: 1':
        # Combine date and time columns for daily data
        df['DATE'] = df['date'].astype(str) + ' ' + df['Unnamed: 1'].astype(str)
        # Drop the original columns
        df = df.drop(['date', 'Unnamed: 1'], axis=1)
        logger.info("✓ Detected daily data format (date,,open columns)")
    # Format 3: Simple date column
    elif 'date' in df.columns:
        df['DATE'] = df['date']
        df = df.drop(['date'], axis=1)
        logger.info("✓ Detected simple date format")
    else:
        raise ValueError("Could not find date column in CSV")
    
    # Rename columns to standard format
    column_map = {
        'open': 'OPEN',
        'high': 'HIGH', 
        'low': 'LOW',
        'close': 'CLOSE',
        'volume': 'VOLUME',
        'oi': 'OI'
    }
    df = df.rename(columns=column_map)
    
    # Parse date - handle format like "16-01-2024 00:00:00+05:30"
    def parse_date(date_str):
        try:
            # Remove timezone info for parsing, then make UTC
            date_part = str(date_str).split('+')[0].strip()
            # Parse DD-MM-YYYY format
            if '-' in date_part and len(date_part.split('-')[0]) <= 2:
                dt = pd.to_datetime(date_part, format='%d-%m-%Y %H:%M:%S')
            else:
                dt = pd.to_datetime(date_part)
            return dt.tz_localize('UTC')
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return pd.NaT
    
    df['DATE'] = df['DATE'].apply(parse_date)
    df = df.dropna(subset=['DATE'])
    df = df.sort_values('DATE').reset_index(drop=True)
    
    logger.info("✅ Loaded %d rows from %s to %s", 
                len(df), df['DATE'].min(), df['DATE'].max())
    
    return df


def build_continuous_instrument(cfg: ConverterConfig) -> FuturesContract:
    """Create a synthetic continuous futures contract.
    
    Example ID: NIFTY_CONTINUOUS.FUT.NSE
    This represents a rolled/continuous contract without specific expiry.
    """
    symbol_str = f"{cfg.symbol}_CONTINUOUS.FUT"
    iid = InstrumentId(symbol=Symbol(symbol_str), venue=Venue(cfg.venue))
    
    now_utc = datetime.now(timezone.utc)
    # Set expiry far in future for continuous contract (10 years)
    expiry_dt = datetime(2035, 12, 31, 23, 59, tzinfo=timezone.utc)
    
    instrument = FuturesContract(
        instrument_id=iid,
        raw_symbol=Symbol(symbol_str),
        asset_class=AssetClass.INDEX,
        currency=Currency.from_str("INR"),
        price_precision=cfg.price_precision,
        price_increment=Price(cfg.price_increment, cfg.price_precision),
        multiplier=Quantity(cfg.multiplier, 0),
        lot_size=Quantity(1, 0),
        underlying=f"{cfg.symbol}.{cfg.venue}.INDEX",
        activation_ns=0,
        expiration_ns=dt_to_unix_nanos(expiry_dt),
        ts_event=dt_to_unix_nanos(now_utc),
        ts_init=dt_to_unix_nanos(now_utc),
        exchange=cfg.venue,
    )
    logger.info("🛠️  Built Continuous FuturesContract %s", instrument.id)
    return instrument


def build_bars(
    df: pd.DataFrame, iid: InstrumentId, interval: str, precision: int
) -> List[Bar]:
    """Build Nautilus Bar objects from DataFrame."""
    bar_type = BarType.from_str(f"{iid}-{interval}-LAST-EXTERNAL")
    bars: list[Bar] = []
    
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(row["DATE"])
        volume_val = float(row.get("VOLUME", 0) or 0)
        
        bar = Bar(
            bar_type=bar_type,
            open=Price(float(row["OPEN"]), precision),
            high=Price(float(row["HIGH"]), precision),
            low=Price(float(row["LOW"]), precision),
            close=Price(float(row["CLOSE"]), precision),
            volume=Quantity(volume_val, 0),
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)
    
    logger.info("📝 Built %d Bars", len(bars))
    return bars


def write_catalog(cfg: ConverterConfig, instrument: FuturesContract, bars: List[Bar]):
    """Persist instrument and bars to Parquet catalog."""
    catalog = ParquetDataCatalog(cfg.destination_catalog)
    catalog.write_data([instrument])
    bars.sort(key=lambda b: b.ts_init)
    catalog.write_data(bars)
    logger.info(
        "✅ Wrote %d bars for instrument %s to %s",
        len(bars),
        instrument.id,
        cfg.destination_catalog,
    )


def build_bar_metadata(df: pd.DataFrame, iid_str: str, extra_fields: List[str]):
    """Build bar-level metadata DataFrame."""
    records = []
    for _, row in df.iterrows():
        rec = {
            "instrument_id": iid_str,
            "timestamp": dt_to_unix_nanos(row["DATE"]),
            "last": row.get("CLOSE"),
        }
        for field in extra_fields:
            val = row.get(field) or row.get(field.upper()) or row.get(field.lower())
            rec[field] = val
        records.append(rec)
    return pd.DataFrame(records)


def write_meta(cfg: ConverterConfig, instrument: FuturesContract, bar_meta_df: pd.DataFrame):
    """Write metadata files."""
    meta_dir = Path(cfg.destination_meta)
    meta_dir.mkdir(parents=True, exist_ok=True)
    
    # Bar-level metadata
    bar_meta_path = meta_dir / "bar_metadata.parquet"
    if bar_meta_path.exists() and not cfg.clean:
        existing = pd.read_parquet(bar_meta_path)
        bar_meta_df = pd.concat([existing, bar_meta_df], ignore_index=True).drop_duplicates(
            subset=["instrument_id", "timestamp"], keep="last"
        )
    bar_meta_df.to_parquet(bar_meta_path, index=False)
    
    # Instrument metadata
    inst_record = {
        "instrument_id": str(instrument.id),
        "symbol": instrument.raw_symbol.value,
        "strike": None,
        "expiry": instrument.expiration_ns,
        "option_kind": "FUT_CONTINUOUS",
        "venue": cfg.venue,
        "activation_ns": instrument.activation_ns,
    }
    
    inst_path = meta_dir / "instruments.parquet"
    df_inst_new = pd.DataFrame([inst_record])
    if inst_path.exists() and not cfg.clean:
        df_inst_old = pd.read_parquet(inst_path)
        df_inst = pd.concat([df_inst_old, df_inst_new], ignore_index=True).drop_duplicates(
            subset=["instrument_id"], keep="last"
        )
    else:
        df_inst = df_inst_new
    df_inst.to_parquet(inst_path, index=False)
    
    logger.info("📑 Wrote metadata to %s", meta_dir)


def run_conversion(cfg: ConverterConfig):
    """Main conversion pipeline."""
    if cfg.data_kind != "bar":
        raise NotImplementedError("Only bar data conversion is implemented")
    
    clear_catalog_dirs(cfg)
    
    # Load continuous futures CSV
    df = load_continuous_csv(cfg.source_csv)
    
    # Build single continuous instrument
    instrument = build_continuous_instrument(cfg)
    
    # Build bars
    bars = build_bars(df, instrument.id, cfg.bar_interval, cfg.price_precision)
    
    # Write to catalog
    write_catalog(cfg, instrument, bars)
    
    # Build and write metadata
    bar_meta_df = build_bar_metadata(df, str(instrument.id), cfg.extra_meta_fields)
    write_meta(cfg, instrument, bar_meta_df)
    
    logger.info(
        "🎉 Conversion complete: %d bars for continuous contract %s",
        len(bars),
        instrument.id
    )
    
    # Update DATA_CATALOG.md
    update_data_catalog(cfg, instrument, len(bars), df['DATE'].min(), df['DATE'].max())


def update_data_catalog(cfg: ConverterConfig, instrument, bar_count: int, 
                        start_date, end_date):
    """Update the data catalog markdown file."""
    catalog_file = Path("DATA_CATALOG.md")
    
    conversion_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    catalog_content = f"""# Data Catalog - Continuous Futures

**Last Updated**: {conversion_timestamp}  
**Source CSV**: `{cfg.source_csv}`

## Available Data

| Instrument ID | Type | Bars | Start Date | End Date | Catalog Path |
|--------------|------|------|------------|----------|--------------|
| {instrument.id} | Continuous Futures | {bar_count} | {start_date} | {end_date} | {cfg.destination_catalog} |

## Metadata Location

- **Bar Metadata**: `{cfg.destination_meta}/bar_metadata.parquet`
- **Instruments**: `{cfg.destination_meta}/instruments.parquet`

## Usage

```bash
# Run backtest on continuous contract
python scripts/v1/backtesting/run_backtest.py \\
    --strategy nd_tt_v4 \\
    --instrument_id {instrument.id} \\
    --catalog_path {cfg.destination_catalog}

# With date range filtering
python scripts/v1/backtesting/run_backtest.py \\
    --strategy nd_tt_v4 \\
    --instrument_id {instrument.id} \\
    --catalog_path {cfg.destination_catalog} \\
    --start_time 2024-01-01 \\
    --end_time 2024-12-31
```
"""
    
    with open(catalog_file, "w", encoding="utf-8") as f:
        f.write(catalog_content)
    
    logger.info("🗒️  Updated DATA_CATALOG.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CSV → Parquet converter for continuous futures"
    )
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing catalog before writing"
    )
    args = parser.parse_args()
    
    config = ConverterConfig.from_yaml(args.config)
    if args.clean:
        config.clean = True
    run_conversion(config)

