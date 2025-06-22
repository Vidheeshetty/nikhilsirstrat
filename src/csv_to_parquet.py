import pandas as pd
import os

def convert_csv_to_parquet(csv_path, parquet_path=None):
    """
    Convert a CSV file to Parquet format.
    
    Args:
        csv_path (str): Path to the input CSV file
        parquet_path (str, optional): Path for the output Parquet file. 
                                    If not provided, will use same name as CSV with .parquet extension
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    if parquet_path is None:
        parquet_path = os.path.splitext(csv_path)[0] + '.parquet'
    
    # Read CSV file
    print(f"Reading CSV file: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Convert to Parquet
    print(f"Converting to Parquet: {parquet_path}")
    df.to_parquet(parquet_path, index=False)
    print("Conversion completed successfully!")

if __name__ == "__main__":
    # Example usage
    csv_file = "data/sample_data.csv"  # Updated to new root-level data directory
    convert_csv_to_parquet(csv_file) 