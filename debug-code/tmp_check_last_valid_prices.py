import pandas as pd
import struct

parquet_path = "catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet"
df = pd.read_parquet(parquet_path)

last_valid_prices = []
for i in range(len(df) - 1, -1, -1):
    try:
        bid = df.iloc[i]["bid_price"]
        ask = df.iloc[i]["ask_price"]
        if isinstance(bid, bytes):
            bid = struct.unpack("d", bid[:8])[0]
        if isinstance(ask, bytes):
            ask = struct.unpack("d", ask[:8])[0]
        if (
            isinstance(bid, (int, float))
            and isinstance(ask, (int, float))
            and bid > 0
            and ask > 0
            and bid < 100000
            and ask < 100000
            and not pd.isna(bid)
            and not pd.isna(ask)
        ):
            mid = (bid + ask) / 2
            last_valid_prices.append({"row": i, "bid": bid, "ask": ask, "mid": mid})
            if len(last_valid_prices) == 10:
                break
    except Exception as e:
        continue
if last_valid_prices:
    print("Last 10 valid prices (from last to first found):")
    for p in last_valid_prices:
        print(f"  Row {p['row']}: bid={p['bid']}, ask={p['ask']}, mid={p['mid']}")
else:
    print("No valid price found.")
