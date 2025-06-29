import pandas as pd
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import QuoteTick
from datetime import datetime

# Instrument to investigate
instrument_id = InstrumentId(
    symbol=Symbol("NIFTY.OPT.03Jul2025.22800.CALL"), venue=Venue("NSE")
)

print(f"Investigating timestamps for: {instrument_id.value}")
print("=" * 80)

# Check CSV timestamps
csv_files = [
    ("2025-06-18", "data/options/nse/nifty/NIFTY_2025-06-18.csv"),
    ("2025-06-19", "data/options/nse/nifty/NIFTY_2025-06-19.csv"),
    ("2025-06-20", "data/options/nse/nifty/NIFTY_2025-06-20.csv"),
]

symbol = "NIFTY.NSE.OPT.31Jul2025.22800.CALL"

print("CSV Timestamps:")
for date, csv_file in csv_files:
    df = pd.read_csv(csv_file)
    df_instrument = df[df["symbol"] == symbol]

    if len(df_instrument) > 0:
        print(f"\n{date}:")
        for _, row in df_instrument.iterrows():
            timestamp = pd.to_datetime(row["timestamp"])
            print(f"  {timestamp}: bid={row['bid']}, ask={row['ask']}")
    else:
        print(f"\n{date}: No data found")

# Check Parquet timestamps
print("\n" + "=" * 80)
print("Parquet Timestamps (first 20 and last 20):")

catalog_dir = "catalog-data/my_nse_strategy/catalog"
catalog = ParquetDataCatalog(catalog_dir)

ticks = catalog.query(data_cls=QuoteTick, identifiers=[instrument_id.value])

if len(ticks) > 0:
    print(f"\nFirst 20 timestamps:")
    for i, tick in enumerate(ticks[:20]):
        dt = datetime.fromtimestamp(tick.ts_init / 1e9)
        print(
            f"  {i + 1:2d}. {dt}: bid={float(tick.bid_price):.2f}, ask={float(tick.ask_price):.2f}"
        )

    print(f"\nLast 20 timestamps:")
    for i, tick in enumerate(ticks[-20:]):
        dt = datetime.fromtimestamp(tick.ts_init / 1e9)
        print(
            f"  {len(ticks) - 19 + i:2d}. {dt}: bid={float(tick.bid_price):.2f}, ask={float(tick.ask_price):.2f}"
        )

    # Check for duplicate timestamps
    timestamps = [tick.ts_init for tick in ticks]
    unique_timestamps = set(timestamps)
    print(f"\nTimestamp Analysis:")
    print(f"  Total ticks: {len(ticks)}")
    print(f"  Unique timestamps: {len(unique_timestamps)}")
    print(f"  Duplicate timestamps: {len(ticks) - len(unique_timestamps)}")

    if len(ticks) != len(unique_timestamps):
        print("  ⚠️ WARNING: Duplicate timestamps found!")

        # Find the most common timestamps
        from collections import Counter

        timestamp_counts = Counter(timestamps)
        most_common = timestamp_counts.most_common(5)
        print(f"  Most common timestamps:")
        for ts, count in most_common:
            dt = datetime.fromtimestamp(ts / 1e9)
            print(f"    {dt}: {count} times")
else:
    print("No Parquet data found")
