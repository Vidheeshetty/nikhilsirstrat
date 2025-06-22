import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
from typing import List

def csv_to_parquet(csv_path, parquet_path):
    """
    Convert a CSV file in the root-level data directory to Parquet format.
    """
    df = pd.read_csv(csv_path)
    table = pa.Table.from_pandas(df)
    pq.write_table(table, parquet_path)

def load_atm_call_options_from_csvs(csv_dir: str) -> pd.DataFrame:
    """
    Loads and processes 15-min snapshot CSVs for ATM CALL options with nearest expiry.
    Args:
        csv_dir (str): Directory containing raw CSV files.
    Returns:
        pd.DataFrame: Cleaned DataFrame with only ATM CALL options for nearest expiry.
    """
    # Gather all CSV files
    csv_files = [os.path.join(csv_dir, f) for f in os.listdir(csv_dir) if f.endswith('.csv')]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {csv_dir}")

    # Load all CSVs into a single DataFrame
    df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
    
    # Basic validation
    if df.empty:
        print("Warning: No data loaded from CSV files")
        return pd.DataFrame()
    
    # Check required columns exist
    required_columns = ['timestamp', 'expiry', 'strike', 'option_type', 'bid', 'ask', 'last', 'volume', 'open_interest']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {df.columns.tolist()}")
        return pd.DataFrame()

    # Ensure correct dtypes
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['expiry'] = pd.to_datetime(df['expiry'])
    df['strike'] = df['strike'].astype(float)
    df['bid'] = df['bid'].astype(float)
    df['ask'] = df['ask'].astype(float)
    df['last'] = df['last'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['open_interest'] = df['open_interest'].astype(float)

    # Filter for nearest expiry
    nearest_expiry = df['expiry'].min()
    df = df[df['expiry'] == nearest_expiry]

    # Only CALL options (handle both 'CALL' and 'CE' formats)
    df = df[df['option_type'].str.upper().isin(['CALL', 'CE'])]
    
    if df.empty:
        print("Warning: No CALL options found after filtering")
        return pd.DataFrame()

    # For each timestamp, find ATM strike (strike closest to median strike)
    result_rows = []
    
    # Get unique timestamps
    unique_timestamps = df['timestamp'].unique()
    
    for ts in unique_timestamps:
        # Get data for this timestamp
        mask = df['timestamp'] == ts
        group = df[mask].copy()  # Create a copy to avoid SettingWithCopyWarning
        
        if len(group) == 0:
            continue
            
        # Find the strike closest to the median strike (proxy for ATM)
        median_strike = group['strike'].median()
        group['strike_diff'] = abs(group['strike'] - median_strike)
        atm_row = group.loc[group['strike_diff'].idxmin()]
        
        # Convert to dictionary, excluding the temporary column
        row_dict = atm_row.drop('strike_diff').to_dict()
        result_rows.append(row_dict)
    
    if not result_rows:
        print("Warning: No ATM rows found")
        return pd.DataFrame()
    
    # Create DataFrame from list of dictionaries
    result_df = pd.DataFrame(result_rows)
    
    # Sort by timestamp
    result_df = result_df.sort_values('timestamp').reset_index(drop=True)
    
    return result_df

# Example usage (uncomment to test)
# df = load_atm_call_options_from_csvs('data/nse')
# print(df.head()) 