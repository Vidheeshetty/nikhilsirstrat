import pandas as pd

symbol = "NIFTY.NSE.OPT.31Jul2025.22800.CALL"
csv_files = [
    ("2025-06-18", "data/options/nse/nifty/NIFTY_2025-06-18.csv"),
    ("2025-06-19", "data/options/nse/nifty/NIFTY_2025-06-19.csv"),
    ("2025-06-20", "data/options/nse/nifty/NIFTY_2025-06-20.csv"),
]

results = []
for date, csv_file in csv_files:
    df = pd.read_csv(csv_file)
    df_instrument = df[df["symbol"] == symbol]
    total = len(df_instrument)
    zero_bids = (df_instrument["bid"] == 0).sum()
    zero_asks = (df_instrument["ask"] == 0).sum()
    results.append(
        {
            "date": date,
            "total_rows": total,
            "zero_bids": zero_bids,
            "zero_asks": zero_asks,
        }
    )

print("CSV zero bid/ask counts per day:")
for r in results:
    print(
        f"{r['date']}: total_rows={r['total_rows']}, zero_bids={r['zero_bids']}, zero_asks={r['zero_asks']}"
    )
