#!/usr/bin/env python3
"""
convert_NSER_csv_to_parquet_v1.py
=================================
Convert NSE-R derived historical futures CSV (`data/futures/NSER/test_historical.csv`)
into Nautilus-Trader parquet catalogs.

Assumptions
-----------
CSV columns:
    SYMBOL, DATE (YYYY-MM-DD), EXPIRY_DT, OPEN, HIGH, LOW, CLOSE, OI, IV

We write:
    • daily Bars (LAST price) under catalog-data/my_nse_strategy/catalog
    • bar_metadata.parquet side-table with OI & IV under catalog-meta
"""

from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime, timezone, timedelta
import logging
from typing import List

import pandas as pd

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.instruments.futures_contract import FuturesContract
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# -------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data" / "futures" / "NSER"

SYMBOL = "NIFTY"
VENUE = "NSE"

CATALOG_DIR = PROJECT_ROOT / "catalog-data" / "trend_follow_futures" / "catalog"
CATALOG_META_DIR = (
    PROJECT_ROOT / "catalog-data" / "trend_follow_futures" / "catalog-meta"
)

PRICE_PRECISION = 2
PRICE_INCREMENT = 0.05
LOT_MULTIPLIER = 50
BAR_INTERVAL = "1-DAY"  # daily bars

# -------------------------------------------------------------------------------------


def clear_catalog_dirs() -> None:
    for p in (CATALOG_DIR, CATALOG_META_DIR):
        if p.exists():
            shutil.rmtree(p)
            log.info("🧹 Removed %s", p)
        p.mkdir(parents=True, exist_ok=True)
        log.info("📂 Created %s", p)


def load_all_csvs() -> list[pd.DataFrame]:
    if not CSV_DIR.exists():
        raise FileNotFoundError(CSV_DIR)

    dataframes: list[pd.DataFrame] = []
    for path in CSV_DIR.glob("*.csv"):
        if path.name.startswith("._"):
            continue
        log.info("📖 Reading %s", path.relative_to(PROJECT_ROOT))
        df = pd.read_csv(path)
        if "DATE" not in df.columns:
            log.warning("Skipping %s – missing DATE column", path.name)
            continue
        df["DATE"] = pd.to_datetime(df["DATE"], utc=True)
        df.sort_values("DATE", inplace=True)
        dataframes.append(df)
    if not dataframes:
        raise ValueError(f"No CSV files found in {CSV_DIR}")
    return dataframes


def build_instrument(expiry_str: str) -> FuturesContract:
    """Create a unique FuturesContract with the expiry encoded in the symbol.

    Example resulting instrument ID: ``NIFTY20250627.FUT.NSE`` where ``20250627``
    comes from the EXPIRY_DT column of the CSV.
    """

    # Treat contract as active until very end of the expiry date so the last
    # trading session is tradable. Add 23:59 (hh:mm) to 00:00 timestamp.
    expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    ) + timedelta(hours=23, minutes=59)

    # Encode expiry into symbol to ensure unique instrument per contract month
    symbol_with_expiry = f"{SYMBOL}{expiry_dt.strftime('%Y%m%d')}.FUT"

    iid = InstrumentId(symbol=Symbol(symbol_with_expiry), venue=Venue(VENUE))

    now_utc = datetime.now(timezone.utc)

    instrument = FuturesContract(
        instrument_id=iid,
        raw_symbol=Symbol(symbol_with_expiry),
        asset_class=AssetClass.INDEX,
        currency=Currency.from_str("INR"),
        price_precision=PRICE_PRECISION,
        price_increment=Price(PRICE_INCREMENT, PRICE_PRECISION),
        multiplier=Quantity(LOT_MULTIPLIER, 0),
        lot_size=Quantity(1, 0),
        underlying=f"{SYMBOL}.{VENUE}.INDEX",
        activation_ns=0,
        expiration_ns=dt_to_unix_nanos(expiry_dt),
        ts_event=dt_to_unix_nanos(now_utc),
        ts_init=dt_to_unix_nanos(now_utc),
        exchange=VENUE,
    )
    log.info("🛠️  Built FuturesContract %s", instrument.id)
    return instrument


def build_bars(df: pd.DataFrame, iid: InstrumentId) -> List[Bar]:
    bars: List[Bar] = []
    # Historical bars loaded from disk are considered EXTERNAL source
    bar_type = BarType.from_str(f"{iid}-{BAR_INTERVAL}-LAST-EXTERNAL")

    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(row["DATE"])
        bar = Bar(
            bar_type=bar_type,
            open=Price(float(row["OPEN"]), PRICE_PRECISION),
            high=Price(float(row["HIGH"]), PRICE_PRECISION),
            low=Price(float(row["LOW"]), PRICE_PRECISION),
            close=Price(float(row["CLOSE"]), PRICE_PRECISION),
            volume=Quantity(0.0, 0),  # no volume in CSV
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)
    log.info("📝 Built %d Bars", len(bars))
    return bars


def build_bar_metadata(df: pd.DataFrame, iid_str: str) -> pd.DataFrame:
    records = [
        {
            "instrument_id": iid_str,
            "timestamp": dt_to_unix_nanos(row["DATE"]),
            "impliedVolatility": row.get("IV"),
            "openInterest": row.get("OI"),
            "last": row.get("CLOSE"),
        }
        for _, row in df.iterrows()
    ]
    return pd.DataFrame(records)


def write_catalog(instruments: List[FuturesContract], bars: List[Bar]):
    """Persist instruments and bar data to the Parquet catalog."""
    catalog = ParquetDataCatalog(str(CATALOG_DIR))
    catalog.write_data(instruments)
    bars.sort(key=lambda b: b.ts_init)
    catalog.write_data(bars)
    log.info("✅ Wrote %d bars for %d instruments", len(bars), len(instruments))


def write_meta(meta_df: pd.DataFrame, instruments: List[FuturesContract]):
    """Write auxiliary metadata side-tables for bars and instruments."""

    # 1) Bar-level side table
    meta_df.to_parquet(CATALOG_META_DIR / "bar_metadata.parquet", index=False)

    # 2) Instruments table – one row per contract
    inst_records = [
        {
            "instrument_id": str(inst.id),
            "symbol": inst.raw_symbol.value,
            "strike": None,
            "expiry": inst.expiration_ns,
            "option_kind": "FUT",
            "venue": VENUE,
            "activation_ns": inst.activation_ns,
        }
        for inst in instruments
    ]
    pd.DataFrame(inst_records).to_parquet(
        CATALOG_META_DIR / "instruments.parquet", index=False
    )


def main() -> None:
    clear_catalog_dirs()

    dfs = load_all_csvs()

    instruments_by_expiry: dict[str, FuturesContract] = {}
    all_bars: list[Bar] = []
    all_meta_records: list[pd.DataFrame] = []

    for df in dfs:
        # A single CSV may contain data for multiple expiries – group accordingly
        if "EXPIRY_DT" not in df.columns:
            log.warning("CSV missing EXPIRY_DT column – skipping")
            continue

        for expiry_str, df_group in df.groupby("EXPIRY_DT"):
            expiry_str = str(expiry_str)

            instrument = instruments_by_expiry.get(expiry_str)
            if instrument is None:
                instrument = build_instrument(expiry_str)
                instruments_by_expiry[expiry_str] = instrument

            # Build bars and metadata for this expiry slice
            bars = build_bars(df_group, instrument.id)
            all_bars.extend(bars)

            meta_df = build_bar_metadata(df_group, str(instrument.id))
            all_meta_records.append(meta_df)

    unique_instruments = list(instruments_by_expiry.values())

    # Persist data & metadata
    write_catalog(unique_instruments, all_bars)
    write_meta(pd.concat(all_meta_records, ignore_index=True), unique_instruments)

    log.info(
        "🎉 Conversion complete: %d bars across %d distinct expiry instruments from %d CSV files",
        len(all_bars),
        len(unique_instruments),
        len(dfs),
    )


if __name__ == "__main__":
    main()
