#!/usr/bin/env python3
"""Generic CSV→Parquet converter driven by YAML configuration.

Example:
--------
```bash
python scripts/csv_to_parquet_converter.py --config config/conversion_sample.yaml
```
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

import pandas as pd

from nautilus_trader.core.datetime import dt_to_unix_nanos  # type: ignore
from nautilus_trader.model.data import Bar, BarType  # type: ignore
from nautilus_trader.model.enums import AssetClass  # type: ignore
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue  # type: ignore
from nautilus_trader.model.instruments.futures_contract import FuturesContract  # type: ignore
from nautilus_trader.model.objects import Price, Quantity, Currency  # type: ignore
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog  # type: ignore

# Ensure repository root is importable *before* any project imports.
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.data_adapters.conversion_config import ConverterConfig  # noqa: E402

logger = logging.getLogger("csv_to_parquet_converter")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# --------------------------------------------------------------------------------------
# Helpers (BAR conversion only – extend for quotes/derivatives later)
# --------------------------------------------------------------------------------------


def clear_catalog_dirs(cfg: ConverterConfig) -> None:
    """Create destination folders.  If *cfg.clean* is True remove first."""
    for p in (Path(cfg.destination_catalog), Path(cfg.destination_meta)):
        if cfg.clean and p.exists():
            shutil.rmtree(p)
            logger.info("🧹 Removed %s", p)
        p.mkdir(parents=True, exist_ok=True)
        logger.info("📂 Created %s", p)


def load_csv(cfg: ConverterConfig) -> pd.DataFrame:
    pattern = cfg.source_csv
    if Path(pattern).is_absolute():
        import glob as _glob

        csv_paths = [Path(p) for p in _glob.glob(str(pattern))]
    else:
        csv_paths = list(Path().glob(pattern))  # relative pattern

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
    expiry_dt = datetime.strptime(expiry_clean, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    ) + timedelta(hours=23, minutes=59)

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


def build_bars(
    df: pd.DataFrame, iid: InstrumentId, interval: str, precision: int
) -> List[Bar]:
    bar_type = BarType.from_str(f"{iid}-{interval}-LAST-EXTERNAL")
    bars: list[Bar] = []
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(row["DATE"])
        volume_val = float(
            row.get("VOLUME") or row.get("volume") or row.get("VOL") or 0
        )
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


def write_catalog(
    cfg: ConverterConfig, instruments: List[FuturesContract], bars: List[Bar]
):
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
            rec[field] = (
                row.get(field) or row.get(field.upper()) or row.get(field.lower())
            )
        records.append(rec)
    return pd.DataFrame(records)


def write_meta(
    cfg: ConverterConfig, instruments: List[FuturesContract], bar_meta_df: pd.DataFrame
):
    """Write bar-level and instrument-level metadata side tables."""
    meta_dir = Path(cfg.destination_meta)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # ------------------ BAR-LEVEL METADATA ------------------------------
    bar_meta_path = meta_dir / "bar_metadata.parquet"
    if bar_meta_path.exists() and not cfg.clean:
        existing = pd.read_parquet(bar_meta_path)
        bar_meta_df = pd.concat(
            [existing, bar_meta_df], ignore_index=True
        ).drop_duplicates(subset=["instrument_id", "timestamp"], keep="last")
    bar_meta_df.to_parquet(bar_meta_path, index=False)

    # ------------------ INSTRUMENT SUMMARY ------------------------------
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
    inst_path = meta_dir / "instruments.parquet"
    df_inst_new = pd.DataFrame(inst_records)
    if inst_path.exists() and not cfg.clean:
        df_inst_old = pd.read_parquet(inst_path)
        df_inst = pd.concat(
            [df_inst_old, df_inst_new], ignore_index=True
        ).drop_duplicates(subset=["instrument_id"], keep="last")
    else:
        df_inst = df_inst_new
    df_inst.to_parquet(inst_path, index=False)

    logger.info("📑 Wrote meta files to %s", meta_dir)


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def _validate_interval(interval: str):
    import re

    if not re.match(r"^\d+-(MIN|MINUTE|DAY|HOUR)$", interval):
        raise ValueError(
            f"Unsupported bar_interval '{interval}' – must match <num>-(MIN|MINUTE|DAY|HOUR)"
        )


def run_conversion(cfg: ConverterConfig):
    if cfg.data_kind != "bar":
        raise NotImplementedError("Currently only bar data conversion is implemented")

    _validate_interval(cfg.bar_interval)

    clear_catalog_dirs(cfg)
    df = load_csv(cfg)

    if "EXPIRY_DT" not in df.columns or df["EXPIRY_DT"].isna().all():
        raise ValueError(
            "Futures CSV must contain EXPIRY_DT column with at least one value"
        )

    instruments: list[FuturesContract] = []
    all_bars: list[Bar] = []
    all_meta_frames: list[pd.DataFrame] = []

    for expiry_str, df_slice in df.groupby("EXPIRY_DT"):
        expiry_str = str(expiry_str)

        instrument = build_instrument(cfg, expiry_str)
        instruments.append(instrument)

        bars = build_bars(
            df_slice, instrument.id, cfg.bar_interval, cfg.price_precision
        )
        all_bars.extend(bars)

        meta_df = build_bar_metadata(
            df_slice, str(instrument.id), cfg.extra_meta_fields
        )
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

    # ------------------------------------------------------------------
    # After successful conversion – refresh DATA_CATALOG.md --------------
    def _scan_catalog_with_metadata(root: Path, source_csv: str):
        from datetime import datetime

        parts = []
        for p in root.rglob("*.parquet"):
            # Get file modification time
            mod_time = datetime.fromtimestamp(p.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            parts.append([str(p), p.name, source_csv, mod_time])
        return parts

    # Get source CSV modification time for reference
    import os
    from datetime import datetime
    from glob import glob

    source_files = glob(cfg.source_csv)
    source_csv_info = []
    for csv_file in source_files:
        if os.path.exists(csv_file):
            csv_mod_time = datetime.fromtimestamp(os.path.getmtime(csv_file)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            source_csv_info.append(f"{csv_file} (modified: {csv_mod_time})")

    source_csv_str = "; ".join(source_csv_info) if source_csv_info else cfg.source_csv

    rows = _scan_catalog_with_metadata(Path(cfg.destination_catalog), source_csv_str)

    try:
        from tabulate import tabulate  # optional dependency

        table_md = tabulate(
            rows,
            headers=["Catalog Path", "File", "Source CSV", "Converted"],
            tablefmt="github",
        )
    except Exception:
        # Fallback to crude table
        header = "| Catalog Path | File | Source CSV | Converted |\n|---|---|---|---|\n"
        body = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows)
        table_md = header + body

    # Read existing catalog to merge with new entries (avoid duplicates)
    catalog_file = Path("DATA_CATALOG.md")
    if catalog_file.exists():
        try:
            with open(catalog_file, "r", encoding="utf-8") as fh:
                fh.read()
        except Exception:
            pass

    # Write updated catalog with timestamp
    conversion_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    catalog_header = f"""# Data Catalog

**Last Updated**: {conversion_timestamp}  
**Source CSV Pattern**: `{cfg.source_csv}`

## Available Data

"""

    with open("DATA_CATALOG.md", "w", encoding="utf-8") as fh:
        fh.write(catalog_header + table_md)
    logger.info("🗒️  Refreshed DATA_CATALOG.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV → Parquet converter")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing catalog before writing"
    )
    args = parser.parse_args()

    config = ConverterConfig.from_yaml(args.config)
    if args.clean:
        config.clean = True
    run_conversion(config)
