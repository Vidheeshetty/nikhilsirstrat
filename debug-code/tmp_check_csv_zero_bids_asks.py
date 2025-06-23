import pandas as pd

csv_file = "data/options/nse/nifty/NIFTY_2025-06-18.csv"
symbol = 'NIFTY.NSE.OPT.31Jul2025.22800.CALL'

df = pd.read_csv(csv_file)
df_instrument = df[df['symbol'] == symbol]

zero_bids = (df_instrument['bid'] == 0).sum()
zero_asks = (df_instrument['ask'] == 0).sum()

total = len(df_instrument)

print(f"Instrument: {symbol}")
print(f"Total rows: {total}")
print(f"Rows with bid = 0: {zero_bids}")
print(f"Rows with ask = 0: {zero_asks}")

if zero_bids > 0 or zero_asks > 0:
    print("Sample rows with bid=0 or ask=0:")
    print(df_instrument[(df_instrument['bid'] == 0) | (df_instrument['ask'] == 0)].head(5)) 