from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import QuoteTick
from datetime import datetime
import pandas as pd

instrument_id = InstrumentId(
    symbol=Symbol("NIFTY.OPT.03Jul2025.22800.CALL"), venue=Venue("NSE")
)
catalog_dir = "catalog-data/my_nse_strategy/catalog"
catalog = ParquetDataCatalog(catalog_dir)

ticks = catalog.query(data_cls=QuoteTick, identifiers=[instrument_id.value])

# Build a DataFrame for easier analysis
data = []
for tick in ticks:
    dt = datetime.fromtimestamp(tick.ts_init / 1e9)
    data.append(
        {"date": dt.date(), "bid": float(tick.bid_price), "ask": float(tick.ask_price)}
    )
df = pd.DataFrame(data)

# Group by date and count zeros
grouped = df.groupby("date").agg(
    total_ticks=("bid", "count"),
    zero_bids=("bid", lambda x: (x == 0).sum()),
    zero_asks=("ask", lambda x: (x == 0).sum()),
)

print("Parquet zero bid/ask counts per day:")
print(grouped)
