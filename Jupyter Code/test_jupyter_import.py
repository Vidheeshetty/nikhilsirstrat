#!/usr/bin/env python3
"""
Test script to verify the data loading works correctly.
This can be run from Jupyter to debug import issues.
"""

import sys
import os

# Print current working directory and Python path
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Add src to path
sys.path.append("src")
print("After adding src, Python path:", sys.path)

try:
    from utils.data_utils import load_atm_call_options_from_csvs

    print("✅ Successfully imported load_atm_call_options_from_csvs")

    # Test the function
    atm_df = load_atm_call_options_from_csvs("data/nse")
    print(f"✅ Successfully loaded data: {len(atm_df)} rows")
    print("Columns:", atm_df.columns.tolist())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
