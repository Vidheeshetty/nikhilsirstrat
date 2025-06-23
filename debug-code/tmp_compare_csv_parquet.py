import pandas as pd
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import QuoteTick
from datetime import datetime

# Instrument to compare
instrument_id = InstrumentId(symbol=Symbol("NIFTY.OPT.03Jul2025.22800.CALL"), venue=Venue("NSE"))

print(f"Comparing CSV vs Parquet data for: {instrument_id.value}")
print("=" * 80)

# Read CSV data
csv_file = "data/options/nse/nifty/NIFTY_2025-06-18.csv"
print(f"Reading CSV from: {csv_file}")

# Filter CSV for the specific instrument
df_csv = pd.read_csv(csv_file)
df_csv_filtered = df_csv[df_csv['symbol'] == 'NIFTY.NSE.OPT.31Jul2025.22800.CALL']

print(f"Found {len(df_csv_filtered)} rows in CSV for this instrument")

# Read Parquet data using Nautilus
catalog_dir = "catalog-data/my_nse_strategy/catalog"
catalog = ParquetDataCatalog(catalog_dir)

ticks_parquet = catalog.query(
    data_cls=QuoteTick,
    identifiers=[instrument_id.value]
)

print(f"Found {len(ticks_parquet)} rows in Parquet for this instrument")

# Convert Parquet ticks to a comparable format
parquet_data = []
for tick in ticks_parquet:
    parquet_data.append({
        'timestamp': datetime.fromtimestamp(tick.ts_init / 1e9),
        'bid': float(tick.bid_price),
        'ask': float(tick.ask_price),
        'bid_size': float(tick.bid_size),
        'ask_size': float(tick.ask_size),
        'instrument_id': tick.instrument_id.value
    })

df_parquet = pd.DataFrame(parquet_data)

# Display first 10 rows side by side
print("\n" + "=" * 80)
print("FIRST 10 ROWS COMPARISON")
print("=" * 80)

print("\nCSV Data (first 10 rows):")
if len(df_csv_filtered) > 0:
    # Use the actual CSV column names
    csv_display = df_csv_filtered[['timestamp', 'bid', 'ask', 'totalBuyQuantity', 'totalSellQuantity']].head(10)
    print(csv_display.to_string(index=False))
else:
    print("No CSV data found for this instrument")

print("\nParquet Data (first 10 rows):")
if len(df_parquet) > 0:
    parquet_display = df_parquet[['timestamp', 'bid', 'ask', 'bid_size', 'ask_size']].head(10)
    print(parquet_display.to_string(index=False))
else:
    print("No Parquet data found for this instrument")

# Display last 10 rows side by side
print("\n" + "=" * 80)
print("LAST 10 ROWS COMPARISON")
print("=" * 80)

print("\nCSV Data (last 10 rows):")
if len(df_csv_filtered) > 0:
    csv_display = df_csv_filtered[['timestamp', 'bid', 'ask', 'totalBuyQuantity', 'totalSellQuantity']].tail(10)
    print(csv_display.to_string(index=False))
else:
    print("No CSV data found for this instrument")

print("\nParquet Data (last 10 rows):")
if len(df_parquet) > 0:
    parquet_display = df_parquet[['timestamp', 'bid', 'ask', 'bid_size', 'ask_size']].tail(10)
    print(parquet_display.to_string(index=False))
else:
    print("No Parquet data found for this instrument")

# Statistical comparison
print("\n" + "=" * 80)
print("STATISTICAL COMPARISON")
print("=" * 80)

if len(df_csv_filtered) > 0 and len(df_parquet) > 0:
    print("\nCSV Statistics:")
    print(f"  Bid range: {df_csv_filtered['bid'].min():.2f} to {df_csv_filtered['bid'].max():.2f}")
    print(f"  Ask range: {df_csv_filtered['ask'].min():.2f} to {df_csv_filtered['ask'].max():.2f}")
    print(f"  Zero bids: {(df_csv_filtered['bid'] == 0).sum()}")
    print(f"  Zero asks: {(df_csv_filtered['ask'] == 0).sum()}")
    
    print("\nParquet Statistics:")
    print(f"  Bid range: {df_parquet['bid'].min():.2f} to {df_parquet['bid'].max():.2f}")
    print(f"  Ask range: {df_parquet['ask'].min():.2f} to {df_parquet['ask'].max():.2f}")
    print(f"  Zero bids: {(df_parquet['bid'] == 0).sum()}")
    print(f"  Zero asks: {(df_parquet['ask'] == 0).sum()}")
    
    # Check if data counts match
    print(f"\nData Count Comparison:")
    print(f"  CSV rows: {len(df_csv_filtered)}")
    print(f"  Parquet rows: {len(df_parquet)}")
    print(f"  Match: {'✓' if len(df_csv_filtered) == len(df_parquet) else '✗'}")
    
    # Check if price ranges are similar
    csv_bid_range = df_csv_filtered['bid'].max() - df_csv_filtered['bid'].min()
    parquet_bid_range = df_parquet['bid'].max() - df_parquet['bid'].min()
    csv_ask_range = df_csv_filtered['ask'].max() - df_csv_filtered['ask'].min()
    parquet_ask_range = df_parquet['ask'].max() - df_parquet['ask'].min()
    
    print(f"\nPrice Range Comparison:")
    print(f"  CSV bid range: {csv_bid_range:.2f}")
    print(f"  Parquet bid range: {parquet_bid_range:.2f}")
    print(f"  CSV ask range: {csv_ask_range:.2f}")
    print(f"  Parquet ask range: {parquet_ask_range:.2f}")
    
    # Check for any significant differences
    if abs(csv_bid_range - parquet_bid_range) < 1.0 and abs(csv_ask_range - parquet_ask_range) < 1.0:
        print("✓ Price ranges are very similar - conversion looks good!")
    else:
        print("⚠ Price ranges differ significantly - may need investigation")

else:
    print("Cannot compare statistics - missing data in one or both sources")

# Additional analysis for the data count mismatch
print("\n" + "=" * 80)
print("DATA COUNT ANALYSIS")
print("=" * 80)

if len(df_csv_filtered) != len(df_parquet):
    print(f"⚠ Data count mismatch detected!")
    print(f"  CSV has {len(df_csv_filtered)} rows")
    print(f"  Parquet has {len(df_parquet)} rows")
    
    if len(df_csv_filtered) == 1 and len(df_parquet) > 1:
        print("\nThis suggests the CSV contains only one snapshot/row per instrument,")
        print("while the Parquet contains multiple time-series data points.")
        print("This is expected if the CSV is end-of-day data and Parquet contains intraday data.")
        
        # Show the single CSV row
        print(f"\nSingle CSV row:")
        print(df_csv_filtered[['timestamp', 'symbol', 'bid', 'ask', 'strike', 'expiry']].to_string(index=False))
        
        # Show a few Parquet rows around the same time
        print(f"\nFirst few Parquet rows:")
        print(df_parquet[['timestamp', 'bid', 'ask', 'bid_size', 'ask_size']].head(5).to_string(index=False)) 