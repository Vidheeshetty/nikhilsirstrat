#!/usr/bin/env python3
"""Generic CSV→Parquet converter driven by YAML configuration.

Example:
--------
```bash
python scripts/csv_to_parquet_converter.py --config config/conversion_sample.yaml
```
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is importable *before* any project imports.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import argparse
import logging
import shutil
from datetime import datetime, timezone, timedelta
from typing import List

import pandas as pd

from nautilus_trader.core.datetime import dt_to_unix_nanos  # type: ignore
from nautilus_trader.model.data import Bar, BarType  # type: ignore
from nautilus_trader.model.enums import AssetClass  # type: ignore
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue  # type: ignore
from nautilus_trader.model.instruments.futures_contract import FuturesContract  # type: ignore
from nautilus_trader.model.objects import Price, Quantity, Currency  # type: ignore
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog  # type: ignore

from utils.data_adapters.conversion_config import ConverterConfig

logger = logging.getLogger("csv_to_parquet_converter")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# --------------------------------------------------------------------------------------
# Helpers (BAR conversion only – extend for quotes/derivatives later)
# --------------------------------------------------------------------------------------

def clear_catalog_dirs(cfg: ConverterConfig) -> None:
    for p in (Path(cfg.destination_catalog), Path(cfg.destination_meta)):
        if p.exists():
            shutil.rmtree(p)
            logger.info("🧹 Removed %s", p)
        p.mkdir(parents=True, exist_ok=True)
        logger.info("📂 Created %s", p)


def load_csv(cfg: ConverterConfig) -> pd.DataFrame:
    csv_paths = list(Path().glob(cfg.source_csv))  # glob relative to cwd
    if not csv_paths:
        raise FileNotFoundError(f"No CSV matched pattern {cfg.source_csv}")

    frames: list[pd.DataFrame] = []
    for path in csv_paths:
        logger.info("📖 Reading %s", path)
        df = pd.read_csv(path)
        if "DATE" not in df.columns:
            logger.warning("⚠️  %s missing DATE column – skipped", path.name)
            continue
        df["DATE"] = pd.to_datetime(df["DATE"], utc=True)
        frames.append(df)

    if not frames:
        raise ValueError("No usable CSV files after processing")
    df_all = pd.concat(frames, ignore_index=True).sort_values("DATE")
    return df_all


def build_instrument(cfg: ConverterConfig, expiry_str: str) -> FuturesContract:
    """Create a unique FuturesContract encoding *expiry_str* (YYYY-MM-DD) into the symbol.

    Example resulting instrument ID: ``NIFTY20250627.FUT.NSE``.
    """

    # Convert value to plain 'YYYY-MM-DD' string first
    expiry_clean = str(expiry_str).split(" ")[0]
    expiry_dt = (
        datetime.strptime(expiry_clean, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        + timedelta(hours=23, minutes=59)
    )

    symbol_with_expiry = f"{cfg.symbol}{expiry_dt.strftime('%Y%m%d')}.FUT"

    iid = InstrumentId(symbol=Symbol(symbol_with_expiry), venue=Venue(cfg.venue))

    now_utc = datetime.now(timezone.utc)

    instrument = FuturesContract(
        instrument_id=iid,
        raw_symbol=Symbol(symbol_with_expiry),
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
    logger.info("🛠️  Built FuturesContract %s", instrument.id)
    return instrument


def build_bars(df: pd.DataFrame, iid: InstrumentId, interval: str, precision: int) -> List[Bar]:
    bar_type = BarType.from_str(f"{iid}-{interval}-LAST-EXTERNAL")
    bars: list[Bar] = []
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(row["DATE"])
        bar = Bar(
            bar_type=bar_type,
            open=Price(float(row["OPEN"]), precision),
            high=Price(float(row["HIGH"]), precision),
            low=Price(float(row["LOW"]), precision),
            close=Price(float(row["CLOSE"]), precision),
            volume=Quantity(0.0, 0),
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)
    logger.info("📝 Built %d Bars", len(bars))
    return bars


def write_catalog(cfg: ConverterConfig, instruments: List[FuturesContract], bars: List[Bar]):
    """Persist *all* instruments and bars into a single Parquet catalog."""
    catalog = ParquetDataCatalog(cfg.destination_catalog)
    catalog.write_data(instruments)
    bars.sort(key=lambda b: b.ts_init)
    catalog.write_data(bars)
    logger.info(
        "✅ Wrote %d bars across %d instruments to %s",
        len(bars),
        len(instruments),
        cfg.destination_catalog,
    )


# --------------------------------------------------------------------------------------
# Metadata helpers
# --------------------------------------------------------------------------------------

def build_bar_metadata(df: pd.DataFrame, iid_str: str, extra_fields: List[str]):
    """Return DataFrame of bar-level metadata limited to *extra_fields*."""
    records = []
    for _, row in df.iterrows():
        rec = {
            "instrument_id": iid_str,
            "timestamp": dt_to_unix_nanos(row["DATE"]),
            "last": row.get("CLOSE"),
        }
        for field in extra_fields:
            rec[field] = row.get(field) or row.get(field.upper()) or row.get(field.lower())
        records.append(rec)
    return pd.DataFrame(records)


def write_meta(cfg: ConverterConfig, instruments: List[FuturesContract], bar_meta_df: pd.DataFrame):
    """Write bar-level and instrument-level metadata side tables."""
    meta_dir = Path(cfg.destination_meta)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Bar-level metadata
    bar_meta_df.to_parquet(meta_dir / "bar_metadata.parquet", index=False)

    # Instrument summary table
    inst_records = [
        {
            "instrument_id": str(inst.id),
            "symbol": inst.raw_symbol.value,
            "strike": None,
            "expiry": inst.expiration_ns,
            "option_kind": "FUT",
            "venue": cfg.venue,
            "activation_ns": inst.activation_ns,
        }
        for inst in instruments
    ]
    pd.DataFrame(inst_records).to_parquet(meta_dir / "instruments.parquet", index=False)
    logger.info("📑 Wrote meta files to %s", meta_dir)


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def run_conversion(cfg: ConverterConfig):
    if cfg.data_kind != "bar":
        raise NotImplementedError("Currently only bar data conversion is implemented")

    clear_catalog_dirs(cfg)
    df = load_csv(cfg)

    if "EXPIRY_DT" not in df.columns or df["EXPIRY_DT"].isna().all():
        raise ValueError("Futures CSV must contain EXPIRY_DT column with at least one value")

    instruments: list[FuturesContract] = []
    all_bars: list[Bar] = []
    all_meta_frames: list[pd.DataFrame] = []

    for expiry_str, df_slice in df.groupby("EXPIRY_DT"):
        expiry_str = str(expiry_str)

        instrument = build_instrument(cfg, expiry_str)
        instruments.append(instrument)

        bars = build_bars(df_slice, instrument.id, cfg.bar_interval, cfg.price_precision)
        all_bars.extend(bars)

        meta_df = build_bar_metadata(df_slice, str(instrument.id), cfg.extra_meta_fields)
        all_meta_frames.append(meta_df)

    write_catalog(cfg, instruments, all_bars)

    bar_meta_df = pd.concat(all_meta_frames, ignore_index=True)
    write_meta(cfg, instruments, bar_meta_df)

    logger.info(
        "🎉 Conversion complete: %d bars across %d expiry instruments from %d CSV rows",
        len(all_bars),
        len(instruments),
        len(df),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV → Parquet converter")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    config = ConverterConfig.from_yaml(args.config)
    run_conversion(config) 