from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import QuoteTick

# Path to the catalog directory
catalog_dir = "catalog-data/my_nse_strategy/catalog"

# Instrument ID for the test
instrument_id = InstrumentId(
    symbol=Symbol("NIFTY.OPT.03Jul2025.22800.CALL"), venue=Venue("NSE")
)

# Load the catalog
catalog = ParquetDataCatalog(catalog_dir)

# Read quote ticks for the instrument using Nautilus's query method
ticks = catalog.query(data_cls=QuoteTick, identifiers=[instrument_id.value])

print(f"Found {len(ticks)} quote ticks for {instrument_id.value}")
print(f"First 10 rows of bid/ask prices:")

for i, tick in enumerate(ticks[:10]):
    bid = tick.bid_price
    ask = tick.ask_price
    print(f"Row {i}: bid={float(bid):.2f}, ask={float(ask):.2f}")

# Also check the last 10 prices to see the range
if len(ticks) > 10:
    print(f"\nLast 10 rows of bid/ask prices:")
    for i, tick in enumerate(ticks[-10:]):
        bid = tick.bid_price
        ask = tick.ask_price
        print(f"Row {len(ticks) - 10 + i}: bid={float(bid):.2f}, ask={float(ask):.2f}")

# Check if prices look reasonable (should be positive and in a reasonable range for options)
print(f"\nPrice validation:")
if ticks:
    all_bids = [float(tick.bid_price) for tick in ticks]
    all_asks = [float(tick.ask_price) for tick in ticks]

    print(f"Bid range: {min(all_bids):.2f} to {max(all_bids):.2f}")
    print(f"Ask range: {min(all_asks):.2f} to {max(all_asks):.2f}")

    # Check for any negative or extremely large prices
    negative_bids = [b for b in all_bids if b <= 0]
    negative_asks = [a for a in all_asks if a <= 0]
    large_bids = [b for b in all_bids if b > 10000]  # Unreasonable for options
    large_asks = [a for a in all_asks if a > 10000]

    if negative_bids:
        print(f"WARNING: Found {len(negative_bids)} negative bid prices!")
    if negative_asks:
        print(f"WARNING: Found {len(negative_asks)} negative ask prices!")
    if large_bids:
        print(f"WARNING: Found {len(large_bids)} extremely large bid prices!")
    if large_asks:
        print(f"WARNING: Found {len(large_asks)} extremely large ask prices!")

    if not negative_bids and not negative_asks and not large_bids and not large_asks:
        print("✓ All prices look reasonable!")
else:
    print("No ticks found!")
