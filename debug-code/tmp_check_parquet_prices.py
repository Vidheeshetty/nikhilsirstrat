import pyarrow.parquet as pq
from nautilus_trader.model.objects import Price

parquet_path = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.03Jul2025.22800.CALL.NSE/part-0.parquet"

table = pq.read_table(parquet_path)
df = table.to_pandas()

print("First 10 rows of bid/ask prices:")
for i, row in df.head(10).iterrows():
    bid = row["bid_price"]
    ask = row["ask_price"]
    # If these are Price objects, print as float; else print raw
    if isinstance(bid, Price):
        bid_val = float(bid)
    else:
        bid_val = bid
    if isinstance(ask, Price):
        ask_val = float(ask)
    else:
        ask_val = ask
    print(f"Row {i}: bid={bid_val}, ask={ask_val}")
