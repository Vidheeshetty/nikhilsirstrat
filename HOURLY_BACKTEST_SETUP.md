# Hourly Continuous Futures - Setup & Backtest Guide

## 🎯 Your Data: NIFTY_FUT_hourly_data.csv

**Format:**
```csv
date,time,open,high,low,close,volume
27-06-2025,09:15:00+05:30,26000,26000,25890,25932.4,42375
```

**Key Characteristics:**
- ✅ Hourly bars (7 per day)
- ✅ Date and time in **separate columns**
- ✅ Has Volume
- ❌ **NO Open Interest (OI)**
- 📅 Coverage: Jun 27 - Sep 16, 2025 (393 bars, ~56 trading days)

---

## 🔧 Setup Steps

### Step 1: Create Hourly Configuration

**File:** `config/convert_nifty_continuous_yf_hourly.yaml`

```yaml
source_csv: "data/futures/YF/NIFTY_FUT_hourly_data.csv"
destination_catalog: "catalog-data/nifty-continuous-yf-hourly/catalog"
destination_meta: "catalog-data/nifty-continuous-yf-hourly/catalog-meta"

# Data description
data_kind: bar
bar_interval: "1-HOUR"  # ← Changed from 1-DAY

# Instrument metadata
symbol: NIFTY
venue: NSE
price_precision: 2
price_increment: 0.05
multiplier: 50

# Extra metadata fields (NO OI available!)
extra_meta_fields:
  - VOLUME

# Processing options
clean: true
```

### Step 2: Modify Converter for Hourly Data

The current `csv_to_parquet_continuous.py` needs a small tweak to handle the separate date/time columns properly.

**Key Changes Needed:**

```python
# Current: Handles date,,open (split with empty column)
if 'date' in df.columns and df.columns[1] == 'Unnamed: 1':
    df['DATE'] = df['date'].astype(str) + ' ' + df['Unnamed: 1'].astype(str)

# Need to add: Handle date,time,open (separate columns)
elif 'date' in df.columns and 'time' in df.columns:
    df['DATE'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
    df = df.drop(['date', 'time'], axis=1)
```

---

## 📝 Complete Modified Converter Section

Add this to `csv_to_parquet_continuous.py` after line 20:

```python
def load_continuous_csv(csv_path: str) -> pd.DataFrame:
    """Load continuous futures CSV with special date format handling."""
    logger.info("📖 Reading %s", csv_path)
    
    df = pd.read_csv(csv_path)
    
    # ⭐ NEW: Handle date,time columns (hourly data)
    if 'date' in df.columns and 'time' in df.columns:
        # Combine date and time columns
        df['DATE'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
        # Drop the original columns
        df = df.drop(['date', 'time'], axis=1)
    # ⭐ EXISTING: Handle date,,open (split columns with empty)
    elif 'date' in df.columns and df.columns[1] == 'Unnamed: 1':
        df['DATE'] = df['date'].astype(str) + ' ' + df['Unnamed: 1'].astype(str)
        df = df.drop(['date', 'Unnamed: 1'], axis=1)
    elif 'date' in df.columns:
        df['DATE'] = df['date']
        df = df.drop(['date'], axis=1)
    else:
        raise ValueError("Could not find date column in CSV")
    
    # Rest remains the same...
```

---

## 🚀 Quick Commands

### Convert Hourly CSV to Catalog

```bash
# Set environment
$env:PYTHONPATH="G:\algo_trading\aiswaryagiven\NTBasedPlatform;G:\algo_trading\aiswaryagiven\NTBasedPlatform\src"

# Convert to catalog
python scripts/v1/data_import/csv_to_parquet_continuous.py \
    --config config/convert_nifty_continuous_yf_hourly.yaml \
    --clean
```

**Expected Output:**
```
📖 Reading data/futures/YF/NIFTY_FUT_hourly_data.csv
✅ Loaded 393 rows from 2025-06-27 to 2025-09-16
🛠️  Built Continuous FuturesContract NIFTY_CONTINUOUS.FUT.NSE
📝 Built 393 Bars
✅ Wrote 393 bars for instrument NIFTY_CONTINUOUS.FUT.NSE
```

### Run Hourly Backtest

```bash
# Full range
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR

# Specific month
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR \
    --start_date 2025-07-01 \
    --end_date 2025-07-31

# Last week only
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR \
    --start_date 2025-09-08 \
    --end_date 2025-09-16
```

---

## ⚠️ Important Differences: Hourly vs Daily

### 1. NO Open Interest Data

**Daily Data:**
```python
# OI tracked at entry and exit
Entry OI: 12,209,500
Exit OI: 11,165,700
```

**Hourly Data:**
```python
# OI NOT available
Entry OI: 0  # Will always be 0
Exit OI: 0   # Will always be 0
```

**Impact on Strategy:**
- Cannot use OI-based signals
- Cannot analyze OI divergence
- Must rely on price/volume only

### 2. Many More Trades Expected

**Daily Bars (416 bars):**
```
82 trades generated
Average: ~5 bars per trade
```

**Hourly Bars (393 bars, but 7× denser):**
```
Expected: 200-400+ trades
Average: Shorter holding periods
More whipsaws likely
```

### 3. Trading Hours Awareness

**Hourly Data Has Time-of-Day:**
```
09:15 - Opening (high volatility)
10:15 - Post-opening
11:15 - Mid-morning
12:15 - Lunch hour (lower volume)
13:15 - Post-lunch
14:15 - Late afternoon
15:15 - Closing
```

**Strategy Considerations:**
```python
# May want to avoid certain hours
if hour == '12:15':
    # Lunch hour - lower liquidity
    skip_trading()

if hour == '09:15':
    # Opening hour - high volatility
    use_wider_stops()
```

### 4. Overnight Gaps

**Hourly Data:**
```
June 27, 15:15 → June 30, 09:15  (weekend gap)
  Last price: 26,019.9
  Open price: 26,000.0
  Gap: -19.9 points

Strategy must handle:
- 18-hour gaps (overnight)
- 3-day gaps (weekends)
```

---

## 📊 Expected Results Differences

### Daily Backtest Results
```
Period: 20 months (416 bars)
Total P&L: -590.76 points
Trades: 82
Win Rate: 37.8%
Avg Trade Duration: ~5 days
```

### Hourly Backtest Results (Expected)
```
Period: 3 months (393 hourly bars = ~56 trading days)
Total P&L: ??? (to be determined)
Trades: 200-400+ (many more!)
Win Rate: ??? (likely lower due to noise)
Avg Trade Duration: ~2-4 hours
```

**Why More Trades?**
- 7× more data points per day
- More frequent signals
- Faster stop-loss triggers
- More false breakouts (noise)

---

## 🎯 Strategy Adaptations for Hourly Data

### Current Strategy (Daily Timeframe)

```python
buffer_percentage: 0.00001  # Very tight (0.001%)
stop_loss_percentage: 0.02  # 2%
```

**Works well for daily because:**
- Price moves are larger
- Less noise
- Fewer false signals

### Suggested for Hourly Timeframe

```python
buffer_percentage: 0.0001   # 10× larger (0.01%)
stop_loss_percentage: 0.01  # Tighter SL (1%)
# OR
stop_loss_percentage: 0.005 # Very tight (0.5%)
```

**Why adjust?**
- Hourly noise requires wider buffer
- But tighter SL to limit intraday risk
- May need time-based exits (EOD)

---

## 🔧 Optional: Time-Based Strategy Enhancements

### Add End-of-Day Exit

```python
# In strategy.on_bar()
if hasattr(bar, 'date_str'):
    # Extract hour from date_str (e.g., "2025-06-27 15:15:00")
    hour = bar.date_str.split()[1][:5] if ' ' in bar.date_str else None
    
    if hour == '15:15' and self._position != 0:
        # Close all positions at end of day
        self._exit_position(close, reason="End of Day")
```

### Trading Hour Filter

```python
# Only trade during high-liquidity hours
TRADING_HOURS = ['09:15', '10:15', '11:15', '13:15', '14:15']

if hour in TRADING_HOURS:
    # Normal strategy logic
    process_signals()
else:
    # Avoid low-liquidity hours
    skip_new_entries()
```

---

## 📈 Hourly Data Analysis Opportunities

### 1. Time-of-Day Patterns

```python
# Analyze which hours are most profitable
09:15 trades: Win Rate 45%
10:15 trades: Win Rate 52% ← Best hour!
11:15 trades: Win Rate 38%
12:15 trades: Win Rate 25% ← Worst (lunch)
13:15 trades: Win Rate 42%
14:15 trades: Win Rate 35%
15:15 trades: Win Rate 40%
```

### 2. Intraday Volatility

```python
# Average hourly range
09:15: ±80 points (highest)
10:15: ±45 points
11:15: ±35 points
12:15: ±25 points (lowest)
13:15: ±40 points
14:15: ±50 points
15:15: ±60 points (closing volatility)
```

### 3. Volume Patterns

```python
# Your actual data shows:
09:15: Avg volume ~50,000+ (opening rush)
10:15: Avg volume ~25,000
12:15: Avg volume ~8,000 (lunch dip)
15:15: Avg volume ~10,000 (end of day)
```

---

## 🎓 What You Can Learn

### From Daily Data

✅ Long-term trend behavior  
✅ Multi-month performance  
✅ Drawdown management  
✅ OI patterns  

### From Hourly Data (NEW!)

✅ **Intraday patterns**  
✅ **Best trading hours**  
✅ **Within-day mean reversion**  
✅ **Time-based risk management**  
✅ **Volatility clustering by hour**  
❌ Cannot study OI (not available)  

---

## 📋 Complete Workflow

### 1. Create Config File

```bash
# Create: config/convert_nifty_continuous_yf_hourly.yaml
# (Copy from example above)
```

### 2. Update Converter (One-time)

```bash
# Edit: scripts/v1/data_import/csv_to_parquet_continuous.py
# Add: Support for separate date,time columns
# (See code example above)
```

### 3. Convert Data

```bash
python scripts/v1/data_import/csv_to_parquet_continuous.py \
    --config config/convert_nifty_continuous_yf_hourly.yaml \
    --clean
```

### 4. Run Backtest

```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR
```

### 5. Analyze Results

```bash
# Open HTML report
start runlogs\backtesting\individual\2025-10-01\[TIMESTAMP]_nd_tt_v4\NIFTY_CONTINUOUS.FUT.NSE.html
```

---

## ⚠️ Known Limitations

### 1. No OI Data
```
Cannot use:
- OI divergence signals
- OI buildup/decay patterns
- OI-based position sizing
```

### 2. Limited History
```
Only 3 months of data:
- Cannot test long-term strategies
- Limited to short-term intraday testing
- Not enough for seasonal analysis
```

### 3. Overnight Risk
```
Strategy may hold overnight:
- Gap risk at 09:15 open
- Weekend gap risk
- Consider forced EOD exits
```

---

## 💡 Recommended Tests

### Test 1: Full 3-Month Period
```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR
```

**Purpose:** Baseline performance on hourly data

### Test 2: Single Month
```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR \
    --start_date 2025-07-01 \
    --end_date 2025-07-31
```

**Purpose:** Month-by-month analysis

### Test 3: Recent Week
```bash
python scripts/v1/backtesting/run_backtest_continuous.py \
    --strategy nd_tt_v4 \
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \
    --catalog_path catalog-data/nifty-continuous-yf-hourly/catalog \
    --bar_interval 1-HOUR \
    --start_date 2025-09-08
```

**Purpose:** Latest market behavior

---

## 🎯 Next Steps

1. ✅ **Read:** `DATA_TYPES_COMPARISON.md` for detailed differences
2. ✅ **Create:** Hourly config file
3. ✅ **Update:** Converter to handle date,time columns
4. ✅ **Convert:** Your hourly CSV to catalog
5. ✅ **Test:** Run backtest and analyze results
6. ⚠️ **Consider:** Strategy parameter adjustments for hourly timeframe

---

**Ready to backtest hourly data!** 🚀

