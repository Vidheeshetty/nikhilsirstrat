import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nautilus_trader.model import QuoteTick
from nautilus_trader.model import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog
import pyarrow as pa
import pyarrow.parquet as pq


# Create sample data
def generate_sample_data():
    # Create a date range
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 10)
    dates = pd.date_range(start=start_date, end=end_date, freq="1min")

    # Generate random price data
    np.random.seed(42)  # For reproducibility
    base_price = 150.0
    prices = base_price + np.random.normal(0, 1, len(dates)).cumsum()

    # Create bid and ask prices
    spread = 0.1
    bids = prices - spread / 2
    asks = prices + spread / 2

    # Create the DataFrame
    df = pd.DataFrame(
        {
            "timestamp": dates,
            "bid_price": bids,
            "ask_price": asks,
            "bid_size": 1000,
            "ask_size": 1000,
        }
    )

    return df


# Create and save the data
def save_sample_data():
    # Create catalog directory if it doesn't exist
    catalog = ParquetDataCatalog("./catalog")

    # Generate sample data
    df = generate_sample_data()

    # Create instrument ID
    instrument_id = InstrumentId.from_str("AAPL.NASDAQ")

    # Convert to QuoteTicks
    ticks = []
    for _, row in df.iterrows():
        tick = QuoteTick(
            instrument_id=instrument_id,
            bid_price=Price(row["bid_price"], precision=2),
            ask_price=Price(row["ask_price"], precision=2),
            bid_size=Quantity(row["bid_size"], precision=0),
            ask_size=Quantity(row["ask_size"], precision=0),
            ts_event=row["timestamp"].timestamp()
            * 1_000_000_000,  # Convert to nanoseconds
            ts_init=row["timestamp"].timestamp() * 1_000_000_000,
        )
        ticks.append(tick)

    # Convert ticks to DataFrame
    data = []
    for tick in ticks:
        data.append(
            {
                "instrument_id": str(tick.instrument_id),
                "bid_price": float(tick.bid_price),
                "ask_price": float(tick.ask_price),
                "bid_size": float(tick.bid_size),
                "ask_size": float(tick.ask_size),
                "ts_event": tick.ts_event,
                "ts_init": tick.ts_init,
            }
        )

    df = pd.DataFrame(data)

    # Convert to PyArrow Table
    table = pa.Table.from_pandas(df)

    # Write to Parquet file
    pq.write_table(table, f"{catalog.path}/quote_ticks.parquet")
    print(f"Saved {len(ticks)} quote ticks to catalog")


if __name__ == "__main__":
    save_sample_data()
