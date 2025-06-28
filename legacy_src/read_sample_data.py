import pandas as pd
import pyarrow.parquet as pq
from nautilus_trader.persistence.catalog import ParquetDataCatalog

def read_sample_data():
    # Create catalog instance
    catalog = ParquetDataCatalog("./catalog")
    
    # Read the Parquet file
    df = pd.read_parquet(f"{catalog.path}/quote_ticks.parquet")
    
    # Display basic information
    print("\nDataset Info:")
    print(f"Total rows: {len(df)}")
    print(f"Date range: from {pd.to_datetime(df['ts_event'], unit='ns').min()} to {pd.to_datetime(df['ts_event'], unit='ns').max()}")
    
    # Display first few rows
    print("\nFirst 5 rows:")
    print(df.head())
    
    # Display basic statistics
    print("\nPrice Statistics:")
    print(df[['bid_price', 'ask_price']].describe())
    
    return df

if __name__ == "__main__":
    read_sample_data() 