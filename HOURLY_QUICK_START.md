# Quick Start - Hourly Futures Backtesting

## ⚡ Just Run These Commands

### Step 1: Set Environment
```powershell
$env:PYTHONPATH="G:\algo_trading\aiswaryagiven\NTBasedPlatform;G:\algo_trading\aiswaryagiven\NTBasedPlatform\src"
```

### Step 2: Convert Hourly CSV to Catalog
```powershell
python scripts/v1/data_import/csv_to_parquet_continuous.py --config config/convert_nifty_continuous_yf_hourly.yaml --clean
```

**Expected Output:**
```
📖 Reading data/futures/YF/NIFTY_FUT_hourly_data.csv
✓ Detected hourly data format (date,time columns)
✅ Loaded 393 rows from 2025-06-27 to 2025-09-16
🛠️  Built Continuous FuturesContract NIFTY_CONTINUOUS.FUT.NSE
📝 Built 393 Bars
✅ Wrote 393 bars for instrument NIFTY_CONTINUOUS.FUT.NSE
🎉 Conversion complete
```

### Step 3: Run Hourly Backtest
```powershell
# Full 3-month range
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog --bar_interval 1-HOUR

# Single month (July 2025)
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog --bar_interval 1-HOUR --start_date 2025-07-01 --end_date 2025-07-31

# Recent week
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog --bar_interval 1-HOUR --start_date 2025-09-08
```

---

## 📊 Your Hourly Data

- **File:** `data/futures/YF/NIFTY_FUT_hourly_data.csv`
- **Bars:** 393 hourly bars
- **Period:** June 27 - Sep 16, 2025 (~56 trading days)
- **Timeframe:** 1-HOUR
- **Trading Hours:** 09:15, 10:15, 11:15, 12:15, 13:15, 14:15, 15:15

---

## ⚠️ Key Differences from Daily Data

| Feature | Daily Data | Hourly Data |
|---------|-----------|-------------|
| **Bars** | 416 | 393 |
| **Period** | 20 months | 3 months |
| **Interval** | 1-DAY | 1-HOUR |
| **OI Data** | ✅ Available | ❌ **NOT Available** |
| **Use Case** | Long-term trends | Intraday trading |
| **Expected Trades** | ~82 | ~200-400+ |

---

## 📁 Reports Location

```
runlogs/backtesting/individual/YYYY-MM-DD/HH-MM-SS_nd_tt_v4/
├── NIFTY_CONTINUOUS.FUT.NSE.html  # Open this!
├── NIFTY_CONTINUOUS.FUT.NSE.csv
└── NIFTY_CONTINUOUS.FUT.NSE.json
```

---

## 📚 Full Documentation

- **Detailed Comparison:** `DATA_TYPES_COMPARISON.md`
- **Setup Guide:** `HOURLY_BACKTEST_SETUP.md`
- **Original Daily Guide:** `CONTINUOUS_FUTURES_GUIDE.md`

---

**That's it! Your hourly data is ready to backtest!** 🚀

