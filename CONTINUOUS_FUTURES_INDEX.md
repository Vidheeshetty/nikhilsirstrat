# Continuous Futures - Quick Reference Index

## 📚 Documentation Files (Read These)

### 🚀 Daily Data (Start Here)

#### 1. **Quick Start - Daily** 
📄 **[QUICK_START_CONTINUOUS.md](QUICK_START_CONTINUOUS.md)**
- Essential commands only
- Copy-paste ready
- Quick setup guide

#### 2. **Complete Guide - Daily**
📄 **[CONTINUOUS_FUTURES_GUIDE.md](CONTINUOUS_FUTURES_GUIDE.md)**
- Full step-by-step workflow
- Configuration reference
- Troubleshooting
- Advanced usage

#### 3. **Implementation Summary - Daily** 
📄 **[CONTINUOUS_FUTURES_IMPLEMENTATION_SUMMARY.md](CONTINUOUS_FUTURES_IMPLEMENTATION_SUMMARY.md)**
- Complete technical details
- All files created/modified
- Issues encountered & solutions
- Architecture integration

---

### ⏱️ Hourly Data (New!)

#### 1. **Quick Start - Hourly** 
📄 **[HOURLY_QUICK_START.md](HOURLY_QUICK_START.md)**
- Hourly-specific commands
- 3-month dataset
- Fast setup

#### 2. **Hourly Setup Guide**
📄 **[HOURLY_BACKTEST_SETUP.md](HOURLY_BACKTEST_SETUP.md)**
- Detailed hourly workflow
- Format differences
- Recommended tests

#### 3. **Hourly Implementation & Analysis** ⭐
📄 **[HOURLY_DATA_IMPLEMENTATION_AND_ANALYSIS.md](HOURLY_DATA_IMPLEMENTATION_AND_ANALYSIS.md)**
- Technical changes for hourly support
- **Why both hourly & daily produced 82 trades**
- CSV format auto-detection
- Strategy trading rhythm analysis

---

### 📊 Comparisons & Analysis

#### **Data Types Comparison**
📄 **[DATA_TYPES_COMPARISON.md](DATA_TYPES_COMPARISON.md)**
- Individual contracts vs continuous futures
- Daily vs hourly continuous data
- OI availability matrix
- Use case recommendations

---

## 🛠️ Core Implementation Files

### Data Conversion
- 📜 `scripts/v1/data_import/csv_to_parquet_continuous.py`
- ⚙️ `config/convert_nifty_continuous_yf.yaml`

### Strategy Runner
- 📜 `src/strategies/nd_tt_v4/runner/backtest_runner/continuous_runner.py`
- 📜 `src/strategies/nd_tt_v4/strategy.py` (modified for OI tracking)

### CLI Interface
- 📜 `scripts/v1/backtesting/run_backtest_continuous.py`

---

## ⚡ Quick Commands

### Convert CSV to Catalog
```bash
python scripts/v1/data_import/csv_to_parquet_continuous.py --config config/convert_nifty_continuous_yf.yaml --clean
```

### Run Backtest (Full Range)
```bash
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE
```

### Run Backtest (Date Range)
```bash
python scripts/v1/backtesting/run_backtest_continuous.py --strategy nd_tt_v4 --instrument_id NIFTY_CONTINUOUS.FUT.NSE --start_date 2024-01-01 --end_date 2024-12-31
```

### View Reports
```bash
start runlogs\backtesting\individual\2025-10-01\[TIMESTAMP]_nd_tt_v4\NIFTY_CONTINUOUS.FUT.NSE.html
```

---

## 📊 Your Data

### Daily Continuous Data
- **CSV File:** `data/futures/YF/NIFTY_FUT_daily_data_continous.csv`
- **Date Range:** Jan 16, 2024 → Sep 16, 2025 (416 bars)
- **Instrument:** NIFTY_CONTINUOUS.FUT.NSE
- **Catalog:** `catalog-data/nifty-continuous-yf/catalog`
- **Bar Interval:** 1-DAY
- **OI:** ✅ Available

### Hourly Continuous Data (New!)
- **CSV File:** `data/futures/YF/NIFTY_FUT_hourly_data.csv`
- **Date Range:** Jun 27, 2025 → Sep 16, 2025 (392 bars)
- **Instrument:** NIFTY_CONTINUOUS.FUT.NSE
- **Catalog:** `catalog-data/nifty-continuous-yf-hourly/catalog`
- **Bar Interval:** 1-HOUR
- **OI:** ❌ Not available (data source limitation)

---

## 📁 Report Locations

Reports are saved to:
```
runlogs/backtesting/individual/YYYY-MM-DD/HH-MM-SS_nd_tt_v4/
├── NIFTY_CONTINUOUS.FUT.NSE.html  ← Open this!
├── NIFTY_CONTINUOUS.FUT.NSE.csv
└── NIFTY_CONTINUOUS.FUT.NSE.json
```

**Note:** Single instrument tests go to `individual/`, not `batch/`

---

## ✅ What's Working

### Daily Data
- [x] CSV conversion (416 bars)
- [x] Date range filtering
- [x] OI tracking (entry & exit)
- [x] P&L calculation (-590.76 points)
- [x] Win rate (37.8%)
- [x] HTML/CSV/JSON reports

### Hourly Data (New!)
- [x] CSV conversion (392 bars)
- [x] Automatic format detection (date,time columns)
- [x] Timezone parsing (+05:30 IST)
- [x] Bar interval parameter (1-HOUR)
- [x] P&L calculation (-685.30 points)
- [x] Win rate (31.7%)
- [x] HTML/CSV/JSON reports

### Both
- [x] All linting passed
- [x] Backward compatibility maintained

---

## 🚨 Important Reminders

1. **Set PYTHONPATH** before running scripts:
   ```bash
   # PowerShell
   $env:PYTHONPATH="G:\algo_trading\aiswaryagiven\NTBasedPlatform;G:\algo_trading\aiswaryagiven\NTBasedPlatform\src"
   
   # CMD
   set PYTHONPATH=G:\algo_trading\aiswaryagiven\NTBasedPlatform;G:\algo_trading\aiswaryagiven\NTBasedPlatform\src
   ```

2. **Date format:** Use YYYY-MM-DD (e.g., 2024-01-16)

3. **Reports location:** Check `individual/` folder for single instrument tests

4. **OI tracking:** Now working! Check trades for entry_oi and exit_oi

5. **IV for futures:** Always 0 (IV is for options only)

---

## 📞 Need Help?

### Daily Data
1. **Quick issues?** → Check [QUICK_START_CONTINUOUS.md](QUICK_START_CONTINUOUS.md)
2. **Detailed help?** → See [CONTINUOUS_FUTURES_GUIDE.md](CONTINUOUS_FUTURES_GUIDE.md)
3. **Technical details?** → Read [CONTINUOUS_FUTURES_IMPLEMENTATION_SUMMARY.md](CONTINUOUS_FUTURES_IMPLEMENTATION_SUMMARY.md)

### Hourly Data
1. **Quick start?** → Check [HOURLY_QUICK_START.md](HOURLY_QUICK_START.md)
2. **Setup guide?** → See [HOURLY_BACKTEST_SETUP.md](HOURLY_BACKTEST_SETUP.md)
3. **Technical & Analysis?** → Read [HOURLY_DATA_IMPLEMENTATION_AND_ANALYSIS.md](HOURLY_DATA_IMPLEMENTATION_AND_ANALYSIS.md)

### Comparisons
1. **Data types?** → See [DATA_TYPES_COMPARISON.md](DATA_TYPES_COMPARISON.md)

---

## 🔬 Notable Analysis

**Why did both hourly and daily produce exactly 82 trades?**
→ See [HOURLY_DATA_IMPLEMENTATION_AND_ANALYSIS.md](HOURLY_DATA_IMPLEMENTATION_AND_ANALYSIS.md#the-82-trade-coincidence)

**TL;DR:** It's not a bug! The strategy has a built-in ~5-bar trading rhythm that creates this natural frequency regardless of timeframe.

---

**Last Updated:** October 3, 2025  
**Status:** ✅ Production Ready (Daily + Hourly)

