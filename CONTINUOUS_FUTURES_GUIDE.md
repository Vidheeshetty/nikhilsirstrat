# Continuous Futures Backtesting Guide

This guide explains how to convert continuous futures CSV data to Nautilus catalog format and run backtests with date range filtering.

## Overview

The continuous futures workflow supports:
- ✅ Continuous (rolled) futures contracts without specific expiry dates
- ✅ Date range filtering for backtests
- ✅ Flexible catalog paths
- ✅ Yahoo Finance and other continuous data sources

## Data Format

### Input CSV Format

The continuous futures CSV has this structure:

```csv
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,22138,21964.7,22029.5,5160750,12209500
17-01-2024,00:00:00+05:30,21743.7,21854.75,21563.3,21589.55,11483200,11165700
```

**Key Points:**
- Date and time are separated by a comma (unusual format)
- Date format: `DD-MM-YYYY`
- No EXPIRY_DT column (continuous contract)
- Contains OHLC, volume, and open interest data

### Output Catalog Structure

After conversion, you'll have:

```
catalog-data/nifty-continuous-yf/
├── catalog/                      # Nautilus Parquet catalog
│   ├── bar.parquet
│   └── instrument.parquet
└── catalog-meta/                 # Metadata tables
    ├── bar_metadata.parquet
    └── instruments.parquet
```

## Step-by-Step Workflow

### Step 1: Prepare Your CSV Data

Place your continuous futures CSV in the `data/futures/YF/` directory:

```bash
data/futures/YF/NIFTY_FUT_daily_data_continous.csv
```

### Step 2: Convert CSV to Nautilus Catalog

Run the conversion script:

```bash
python scripts/v1/data_import/csv_to_parquet_continuous.py \
    --config config/convert_nifty_continuous_yf.yaml \
    --clean
```

**What happens:**
1. Reads the CSV and parses the unusual date format
2. Creates a single continuous contract instrument: `NIFTY_CONTINUOUS.FUT.NSE`
3. Converts all bars to Nautilus format
4. Writes to Parquet catalog
5. Updates `DATA_CATALOG.md` with catalog information

**Expected Output:**
```
📖 Reading data/futures/YF/NIFTY_FUT_daily_data_continous.csv
✅ Loaded 416 rows from 2024-01-16 to 2025-09-16
🛠️  Built Continuous FuturesContract NIFTY_CONTINUOUS.FUT.NSE
📝 Built 416 Bars
✅ Wrote 416 bars for instrument NIFTY_CONTINUOUS.FUT.NSE
📑 Wrote metadata to catalog-data/nifty-continuous-yf/catalog-meta
🎉 Conversion complete: 416 bars for continuous contract NIFTY_CONTINUOUS.FUT.NSE
🗒️  Updated DATA_CATALOG.md
```

### Step 3: Verify the Catalog

Check the generated catalog:

```bash
# View catalog summary
cat DATA_CATALOG.md

# Or use Python to inspect
python -c "
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
catalog = ParquetDataCatalog('catalog-data/nifty-continuous-yf/catalog')
print('Instruments:', [str(i.id) for i in catalog.instruments()])
bars = catalog.bars(as_nautilus=False)
print(f'Total bars: {len(bars)}')
"
```

### Step 4: Run Backtest (Full Data Range)

Run backtest on the entire dataset:

```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE
```

### Step 5: Run Backtest with Date Range

Run backtest for a specific period:

```bash
# Test only 2024 data
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --start_date 2024-01-01 \
    --end_date 2024-12-31

# Test only recent data (from June 2025 onwards)
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --start_date 2025-06-01

# Test only up to a certain date
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --end_date 2024-06-30
```

## Configuration Reference

### Conversion Config (`config/convert_nifty_continuous_yf.yaml`)

```yaml
# CSV source file
source_csv: "data/futures/YF/NIFTY_FUT_daily_data_continous.csv"

# Output catalog paths
destination_catalog: "catalog-data/nifty-continuous-yf/catalog"
destination_meta: "catalog-data/nifty-continuous-yf/catalog-meta"

# Data description
data_kind: bar
bar_interval: "1-DAY"

# Instrument metadata
symbol: NIFTY          # Base symbol
venue: NSE             # Exchange
price_precision: 2     # Decimal places
price_increment: 0.05  # Minimum tick size
multiplier: 50         # Contract multiplier

# Extra metadata fields
extra_meta_fields:
  - OI
  - VOLUME

# Processing options
clean: true  # Remove existing catalog before conversion
```

## Advanced Usage

### Custom Catalog Path

Use a different catalog location:

```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path /path/to/custom/catalog
```

### Save Results to JSON

Export results to a JSON file:

```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --start_date 2024-01-01 \
    --end_date 2024-12-31 \
    --outfile results_2024.json
```

### Multiple Time Periods Analysis

Run backtests for different periods to analyze performance:

```bash
# Q1 2024
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --start_date 2024-01-01 \
    --end_date 2024-03-31

# Q2 2024
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --start_date 2024-04-01 \
    --end_date 2024-06-30

# H1 2024
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --start_date 2024-01-01 \
    --end_date 2024-06-30
```

## Understanding the Results

### Console Output

After running a backtest, you'll see:

```
================================================================================
Running Continuous Futures Backtest
================================================================================
Strategy: nd_tt_v4
Instrument: NIFTY_CONTINUOUS.FUT.NSE
Catalog: catalog-data/nifty-continuous-yf/catalog
Date Range: 2024-01-01 → 2024-12-31
================================================================================

Loaded 252 bars from catalog
Running backtest on 252 bars from 2024-01-16 to 2024-12-31

================================================================================
Backtest Results Summary
================================================================================
Total P&L: 1234.50
Number of Trades: 12
Win Rate: 66.7%
Sharpe Ratio: 1.45
Max Drawdown: -5.23%
================================================================================

📊 Full report available at:
   runlogs/backtesting/batch/2025-10-01/14-30-45_nd_tt_v4/summary.html
```

### Report Files

The backtest generates these files:

1. **`summary.html`** - Interactive HTML report with charts and metrics
2. **`trade_details.csv`** - All trades in CSV format
3. **`trade_details.json`** - Complete results in JSON format

## Troubleshooting

### Problem: CSV Not Found

**Error:** `FileNotFoundError: No CSV matched pattern`

**Solution:** Verify the CSV path in your config file matches the actual file location.

### Problem: No Bars After Date Filtering

**Error:** `ValueError: No price data found for ... between ...`

**Solutions:**
- Check date format is YYYY-MM-DD
- Verify dates are within the available data range
- Use `cat DATA_CATALOG.md` to see available date range

### Problem: Import Errors

**Error:** `ModuleNotFoundError`

**Solution:** Set PYTHONPATH [[memory:6109617]]:

```powershell
# PowerShell
$env:PYTHONPATH="G:\algo_trading\aiswaryagiven\NTBasedPlatform;G:\algo_trading\aiswaryagiven\NTBasedPlatform\src"
```

### Problem: Wrong Catalog Path

**Error:** `ValueError: Failed to load data for ...`

**Solutions:**
- Check `--catalog_path` matches your conversion destination
- Default is `catalog-data/nifty-continuous-yf/catalog`
- Verify catalog exists: `ls catalog-data/nifty-continuous-yf/catalog/`

## Comparison: Continuous vs Expiry-Based

### Continuous Futures (This Guide)
- ✅ Single synthetic instrument
- ✅ No expiry rollover handling needed
- ✅ Simpler backtesting (one contract)
- ✅ Good for long-term strategy testing
- ❌ May not reflect actual roll costs

### Expiry-Based Futures (Original System)
- ✅ Multiple instruments per expiry month
- ✅ Realistic expiry handling
- ✅ Can test rollover strategies
- ❌ More complex (many instruments)
- ❌ Requires roll management

## Integration with Existing System

This continuous futures system is **fully compatible** with the existing NT-Based Platform:

- ✅ Uses same `EngineManager` and `DataManager` infrastructure
- ✅ Same reporting system (HTML, CSV, JSON)
- ✅ Same strategy interface
- ✅ Can run both continuous and expiry-based backtests

**Key Files:**
- **Converter:** `scripts/v1/data_import/csv_to_parquet_continuous.py`
- **Runner:** `src/strategies/nd_tt_v4/runner/backtest_runner/continuous_runner.py`
- **CLI:** `scripts/v1/backtesting/run_backtest_continuous.py`
- **Config:** `config/convert_nifty_continuous_yf.yaml`

## Next Steps

1. **Convert your data:** Run the CSV to Parquet conversion
2. **Test with full range:** Run backtest without date filters
3. **Analyze periods:** Use date ranges to analyze specific periods
4. **Compare results:** Compare continuous vs expiry-based backtests
5. **Optimize strategy:** Use results to tune strategy parameters

## Related Documentation

- **Strategy Implementation:** `STRATEGY_IMPLEMENTATION_GUIDE.md`
- **Data Catalog:** `DATA_CATALOG.md` (auto-generated)
- **Original System:** See existing `convert_nifty_continuous.yaml` for expiry-based approach

---

**Questions or Issues?** Check the troubleshooting section or review the conversion logs for detailed error messages.

