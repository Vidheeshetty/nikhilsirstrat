#!/usr/bin/env python3
"""
Diagnostic script to check environment differences.
Run this in both terminal and Jupyter to compare.
"""

import sys
import pandas as pd
import numpy as np
import os

print("=== Environment Diagnostics ===")
print(f"Python version: {sys.version}")
print(f"Pandas version: {pd.__version__}")
print(f"Numpy version: {np.__version__}")
print(f"Working directory: {os.getcwd()}")

# Test DataFrame creation with similar data
print("\n=== Testing DataFrame Creation ===")

# Create test data similar to what we're working with
test_data = [
    {'timestamp': '2025-06-18 12:00:00', 'symbol': 'TEST', 'value': 100},
    {'timestamp': '2025-06-18 12:15:00', 'symbol': 'TEST', 'value': 101},
]

try:
    df1 = pd.DataFrame(test_data)
    print("✅ pd.DataFrame(list_of_dicts) works")
except Exception as e:
    print(f"❌ pd.DataFrame(list_of_dicts) failed: {e}")

# Test with Series objects (like our atm_rows)
test_series = [
    pd.Series({'timestamp': '2025-06-18 12:00:00', 'symbol': 'TEST', 'value': 100}),
    pd.Series({'timestamp': '2025-06-18 12:15:00', 'symbol': 'TEST', 'value': 101}),
]

try:
    df2 = pd.DataFrame(test_series)
    print("✅ pd.DataFrame(list_of_series) works")
except Exception as e:
    print(f"❌ pd.DataFrame(list_of_series) failed: {e}")

# Test with Series objects that have different indices
test_series_diff = [
    pd.Series({'timestamp': '2025-06-18 12:00:00', 'symbol': 'TEST', 'value': 100}, index=['timestamp', 'symbol', 'value']),
    pd.Series({'timestamp': '2025-06-18 12:15:00', 'symbol': 'TEST', 'value': 101}, index=['timestamp', 'symbol', 'value']),
]

try:
    df3 = pd.DataFrame(test_series_diff)
    print("✅ pd.DataFrame(list_of_series_with_index) works")
except Exception as e:
    print(f"❌ pd.DataFrame(list_of_series_with_index) failed: {e}")

print("\n=== Test Results ===")
if 'df1' in locals():
    print(f"df1 shape: {df1.shape}, columns: {df1.columns.tolist()}")
if 'df2' in locals():
    print(f"df2 shape: {df2.shape}, columns: {df2.columns.tolist()}")
if 'df3' in locals():
    print(f"df3 shape: {df3.shape}, columns: {df3.columns.tolist()}") 