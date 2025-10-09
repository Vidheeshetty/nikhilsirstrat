# Quick Start - Continuous Futures Backtesting

## TL;DR - Just Run These Commands

### 1. Set Environment (PowerShell)
```powershell
$env:PYTHONPATH="G:\algo_trading\aiswaryagiven\NTBasedPlatform;G:\algo_trading\aiswaryagiven\NTBasedPlatform\src"
```

### 2. Convert CSV to Catalog
```powershell
python scripts/v1/data_import/csv_to_parquet_continuous.py --config config/convert_nifty_continuous_yf.yaml --clean
```

### 3. Run Backtest (Full Range)
```powershell
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE
```

### 4. Run Backtest with Date Range
```powershell
# 2024 only
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --start_date 2024-01-01 --end_date 2024-12-31

# 2025 only
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --start_date 2025-01-01

# First 6 months of 2024
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --start_date 2024-01-01 --end_date 2024-06-30
```

## What You Get

- ✅ Continuous futures contract: `NIFTY_CONTINUOUS.FUT.NSE`
- ✅ 416 daily bars (Jan 2024 - Sep 2025)
- ✅ Date range filtering support
- ✅ Full HTML reports with charts
- ✅ Trade-by-trade analysis

## Results Location

After running, find your results at:
```
runlogs/backtesting/batch/YYYY-MM-DD/HH-MM-SS_nd_tt_v4/
├── summary.html          # Open this in browser
├── trade_details.csv     # Import to Excel
└── trade_details.json    # For further analysis
```

## Your CSV Structure

Your file: `data/futures/YF/NIFTY_FUT_daily_data_continous.csv`

Format:
```
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,22138,21964.7,22029.5,5160750,12209500
```

Date range: **Jan 16, 2024** → **Sep 16, 2025** (416 rows)

## Common Use Cases

### Test Different Periods
```powershell
# Bull market period (example)
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --start_date 2024-03-01 --end_date 2024-06-30

# Bear market period (example)
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --start_date 2024-10-01 --end_date 2025-01-31
```

### Export Results
```powershell
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --outfile my_results.json
```

## Need More Details?

See `CONTINUOUS_FUTURES_GUIDE.md` for full documentation.

