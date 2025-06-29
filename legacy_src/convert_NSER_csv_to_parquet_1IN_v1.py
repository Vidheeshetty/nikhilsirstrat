#!/usr/bin/env python3
"""
convert_NSER_csv_to_parquet_1IN_v1.py
====================================
Convert **NSE-R monthly futures CSV files** found under
`data/futures/NSER/` into a Nautilus-Trader Parquet catalog **using exactly
one instrument**: ``NIFTY.FUT.NSE``.

Differences vs. `convert_NSER_csv_to_parquet_v1.py`
--------------------------------------------------
1. All rows – irrespective of their `EXPIRY_DT` – are mapped onto a single
   `FuturesContract` (`NIFTY.FUT.NSE`).
2. The contract's `expiration_ns` is set to the **latest** expiry date present
   in the CSVs, so that the instrument remains valid for the full data span.
3. Output locations are unchanged:
   - Core catalog:   ``catalog-data/trend_follow_futures/catalog``
   - Meta catalog:   ``catalog-data/trend_follow_futures/catalog-meta``

Run the script with:
```
python src/convert_NSER_csv_to_parquet_1IN_v1.py
```
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone, timedelta
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

# ----------------------------------------------------------------------------
# Static parameters – edit if your naming conventions differ
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data" / "futures" / "NSER"

SYMBOL = "NIFTY"
VENUE = "NSE"

CATALOG_DIR = PROJECT_ROOT / "catalog-data" / "trend_follow_futures" / "catalog"
META_DIR = PROJECT_ROOT / "catalog-data" / "trend_follow_futures" / "catalog-meta"

PRICE_PRECISION = 2
PRICE_INCREMENT = 0.05  # INR ticks
LOT_MULTIPLIER = 50  # contract size
BAR_INTERVAL = "1-DAY"  # daily bars

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def clear_catalog_dirs() -> None:
    """Delete and recreate parquet catalog & meta directories."""
    for p in (CATALOG_DIR, META_DIR):
        if p.exists():
            shutil.rmtree(p)
            log.info("🧹 Removed %s", p)
        p.mkdir(parents=True, exist_ok=True)
        log.info("📂 Created %s", p)


def load_csv_data() -> pd.DataFrame:
    """Load every CSV in *CSV_DIR* and return a single concatenated DataFrame."""
    if not CSV_DIR.exists():
        raise FileNotFoundError(CSV_DIR)

    frames: list[pd.DataFrame] = []
    for path in CSV_DIR.glob("*.csv"):
        if path.name.startswith("._"):
            continue  # skip macOS resource forks
        log.info("📖 Reading %s", path.relative_to(PROJECT_ROOT))
        df = pd.read_csv(path)
        if "DATE" not in df.columns:
            log.warning("⚠️  %s missing DATE column – skipped", path.name)
            continue
        df["DATE"] = pd.to_datetime(df["DATE"], utc=True)
        frames.append(df)

    if not frames:
        raise ValueError(f"No usable CSV files found in {CSV_DIR}")

    all_data = pd.concat(frames, ignore_index=True)
    all_data.sort_values("DATE", inplace=True)
    return all_data


def build_single_instrument(expiry_ns: int) -> FuturesContract:
    """Return one *FuturesContract* with ID ``NIFTY.FUT.NSE``."""
    iid = InstrumentId(symbol=Symbol("NIFTY.FUT"), venue=Venue(VENUE))

    now_utc = datetime.now(timezone.utc)

    instrument = FuturesContract(
        instrument_id=iid,
        raw_symbol=Symbol("NIFTY.FUT"),
        asset_class=AssetClass.INDEX,
        currency=Currency.from_str("INR"),
        price_precision=PRICE_PRECISION,
        price_increment=Price(PRICE_INCREMENT, PRICE_PRECISION),
        multiplier=Quantity(LOT_MULTIPLIER, 0),
        lot_size=Quantity(1, 0),
        underlying=f"{SYMBOL}.{VENUE}.INDEX",
        activation_ns=0,
        expiration_ns=expiry_ns,
        ts_event=dt_to_unix_nanos(now_utc),
        ts_init=dt_to_unix_nanos(now_utc),
        exchange=VENUE,
    )
    log.info("🛠️  Built single FuturesContract %s", instrument.id)
    return instrument


def build_bars(df: pd.DataFrame, iid: InstrumentId) -> List[Bar]:
    bar_type = BarType.from_str(f"{iid}-{BAR_INTERVAL}-LAST-EXTERNAL")
    bars: list[Bar] = []

    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(row["DATE"])
        bar = Bar(
            bar_type=bar_type,
            open=Price(float(row["OPEN"]), PRICE_PRECISION),
            high=Price(float(row["HIGH"]), PRICE_PRECISION),
            low=Price(float(row["LOW"]), PRICE_PRECISION),
            close=Price(float(row["CLOSE"]), PRICE_PRECISION),
            volume=Quantity(0.0, 0),
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)

    log.info("📝 Built %d Bars", len(bars))
    return bars


def build_meta(df: pd.DataFrame, iid_str: str) -> pd.DataFrame:
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


def write_catalog(instrument: FuturesContract, bars: List[Bar]) -> None:
    catalog = ParquetDataCatalog(str(CATALOG_DIR))
    catalog.write_data([instrument])
    bars.sort(key=lambda b: b.ts_init)
    catalog.write_data(bars)
    log.info("✅ Wrote %d bars for instrument %s", len(bars), instrument.id)


def write_meta(meta_df: pd.DataFrame, instrument: FuturesContract) -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)

    meta_df.to_parquet(META_DIR / "bar_metadata.parquet", index=False)

    pd.DataFrame(
        [
            {
                "instrument_id": str(instrument.id),
                "symbol": instrument.raw_symbol.value,
                "strike": None,
                "expiry": instrument.expiration_ns,
                "option_kind": "FUT",
                "venue": VENUE,
                "activation_ns": instrument.activation_ns,
            }
        ]
    ).to_parquet(META_DIR / "instruments.parquet", index=False)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main() -> None:
    clear_catalog_dirs()

    df_all = load_csv_data()

    # Determine latest expiry in dataset (if column present); otherwise, push far future
    if "EXPIRY_DT" in df_all.columns and not df_all["EXPIRY_DT"].isna().all():
        latest_expiry = pd.to_datetime(df_all["EXPIRY_DT"].dropna().max()).tz_localize(
            "UTC"
        )
    else:
        latest_expiry = datetime(2100, 1, 1, tzinfo=timezone.utc)
    expiry_ns = dt_to_unix_nanos(latest_expiry + timedelta(hours=23, minutes=59))

    instrument = build_single_instrument(expiry_ns)

    bars = build_bars(df_all, instrument.id)

    meta_df = build_meta(df_all, str(instrument.id))

    write_catalog(instrument, bars)
    write_meta(meta_df, instrument)

    log.info(
        "🎉 Conversion complete: %d bars for instrument %s from %d CSV rows",
        len(bars),
        instrument.id,
        len(df_all),
    )


if __name__ == "__main__":
    main()
