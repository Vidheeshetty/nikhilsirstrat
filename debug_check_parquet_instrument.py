import sys
from datetime import datetime
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

# Configurable parameters
CATALOG_PATH = "catalog-data"
INSTRUMENT_ID = "NIFTY.OPT.03Jul2025.22800.CALL.NSE"
START_DATE = "2024-06-18"
END_DATE = "2024-06-22"

start_dt = datetime.fromisoformat(f"{START_DATE}T00:00:00")
end_dt = datetime.fromisoformat(f"{END_DATE}T23:59:59")

print(f"Checking data for instrument: {INSTRUMENT_ID}")
print(f"Date range: {START_DATE} to {END_DATE}")
print(f"Catalog path: {CATALOG_PATH}")

try:
    catalog = ParquetDataCatalog(CATALOG_PATH)
    ticks = catalog.quote_ticks(
        instrument_ids=[INSTRUMENT_ID],
        start=start_dt,
        end=end_dt,
        as_nautilus=True,
    )
    print(f"Found {len(ticks)} ticks.")
    if ticks:
        print(f"First tick timestamp: {ticks[0].ts_event}")
        print(f"Last tick timestamp: {ticks[-1].ts_event}")
        print(f"Sample tick: {ticks[0]}")
    else:
        print("No ticks found for this instrument and date range.")
except Exception as e:
    print(f"Error loading ticks: {e}")
    sys.exit(1)
