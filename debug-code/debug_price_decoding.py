import pandas as pd
import struct

parquet_file = 'catalog-data/my_nse_strategy/catalog/data/quote_tick/NIFTY.OPT.31Jul2025.26000.CALL.NSE/part-0.parquet'
df = pd.read_parquet(parquet_file)

def decode_price(price_bytes):
    # Nautilus Price: 8 bytes int64 value, 1 byte int8 precision
    if isinstance(price_bytes, bytes) and len(price_bytes) >= 9:
        value = struct.unpack('<q', price_bytes[:8])[0]
        precision = price_bytes[8]
        return value / (10 ** precision)
    return None

print('First 10 decoded prices from Parquet:')
for i in range(min(10, len(df))):
    bid = decode_price(df.iloc[i]['bid_price'])
    ask = decode_price(df.iloc[i]['ask_price'])
    print(f'Row {i}: bid={bid}, ask={ask}') 