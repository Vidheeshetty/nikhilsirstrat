# Data Types Comparison - Individual Contracts vs Continuous Futures

## 📊 Three Data Types Explained

### Type 1: Individual Expiry Contracts (Original)
**File:** `raw-data/source=NSER/.../NIFTY_2023.csv`

### Type 2: Daily Continuous Futures
**File:** `data/futures/YF/NIFTY_FUT_daily_data_continous.csv`

### Type 3: Hourly Continuous Futures (NEW)
**File:** `data/futures/YF/NIFTY_FUT_hourly_data.csv`

---

## 🔍 Detailed Comparison

### CSV Format Comparison

| Feature | Individual Contracts | Daily Continuous | Hourly Continuous |
|---------|---------------------|------------------|-------------------|
| **Date Column** | Single `DATE` | Split `date,,` | Separate `date,time` |
| **Date Format** | YYYY-MM-DD | DD-MM-YYYY | DD-MM-YYYY |
| **Time Info** | None (daily close) | 00:00:00+05:30 | HH:MM:SS+05:30 |
| **EXPIRY_DT** | ✅ Required | ❌ Not present | ❌ Not present |
| **SYMBOL** | ✅ NIFTY | ❌ Not present | ❌ Not present |
| **OHLC Columns** | UPPERCASE | lowercase | lowercase |
| **Volume** | ✅ VOLUME | ✅ volume | ✅ volume |
| **OI** | ✅ OI | ✅ oi | ❌ **NOT present** |
| **IV** | ✅ IV (empty) | ❌ Not present | ❌ Not present |

### Sample Data Structure

**Individual Contracts:**
```csv
SYMBOL,DATE,EXPIRY_DT,OPEN,HIGH,LOW,CLOSE,OI,IV
NIFTY,2023-06-01,2023-06-29,18624.95,18659.0,18550.0,18570.0,8833800,
NIFTY,2023-06-01,2023-07-27,18702.0,18735.0,18633.8,18650.35,741950,
```

**Daily Continuous:**
```csv
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,22138,21964.7,22029.5,5160750,12209500
17-01-2024,00:00:00+05:30,21743.7,21854.75,21563.3,21589.55,11483200,11165700
```

**Hourly Continuous:**
```csv
date,time,open,high,low,close,volume
27-06-2025,09:15:00+05:30,26000,26000,25890,25932.4,42375
27-06-2025,10:15:00+05:30,25932.4,25973.9,25904.4,25965.9,24225
27-06-2025,11:15:00+05:30,25965.9,25995,25960,25990,21600
```

---

## 📈 Data Characteristics

### Timeframe & Granularity

| Type | Bars/Day | Total Period | Total Bars | Granularity |
|------|----------|--------------|------------|-------------|
| **Individual** | 1 | Jun-Dec 2023 | ~1500 | Daily close |
| **Daily Continuous** | 1 | Jan 2024-Sep 2025 | 416 | Daily close |
| **Hourly Continuous** | 7 | Jun-Sep 2025 | 393 | Hourly intervals |

**Hourly Trading Hours:**
- 09:15, 10:15, 11:15, 12:15, 13:15, 14:15, 15:15 IST
- **7 bars per trading day**
- **No overnight or weekend data**

### Instrument Structure

**Individual Contracts:**
```
Multiple instruments, one per expiry:
├── NIFTY20230629.FUT.NSE  (Jun 2023 expiry)
├── NIFTY20230727.FUT.NSE  (Jul 2023 expiry)
├── NIFTY20230831.FUT.NSE  (Aug 2023 expiry)
└── ... (28 instruments total)
```

**Continuous Contracts:**
```
Single rolled instrument:
└── NIFTY_CONTINUOUS.FUT.NSE  (synthetic, no real expiry)
```

---

## 🎯 Use Case Differences

### When to Use Individual Contracts

✅ **Best For:**
- Realistic expiry simulation
- Roll strategy testing
- Calendar spread analysis
- Contango/backwardation study
- Actual trading simulation

❌ **Limitations:**
- Complex (multiple instruments)
- Requires rollover handling
- More setup needed

**Example Strategy:**
```python
# Test how to roll between Jun and Jul contracts
if days_to_expiry <= 5:
    exit_current_contract()
    enter_next_contract()
```

### When to Use Daily Continuous

✅ **Best For:**
- Long-term trend analysis
- Strategy backtesting (months/years)
- Daily timeframe strategies
- Simple P&L calculation
- Multi-year performance

❌ **Limitations:**
- No rollover costs reflected
- Single price per day
- Can't test intraday strategies

**Example Strategy:**
```python
# Trend following on daily data
if close > sma_50 and close > yesterday_high:
    enter_long()
```

### When to Use Hourly Continuous

✅ **Best For:**
- Intraday strategy testing
- Scalping/day trading strategies
- Hourly breakout patterns
- Intraday volatility analysis
- Within-day trend capture

❌ **Limitations:**
- No OI data available
- Limited history (few months)
- Higher data volume
- More computational intensive

**Example Strategy:**
```python
# Intraday breakout
if current_hour_high > previous_day_high:
    enter_long_intraday()
if time == '15:15':
    close_all_positions()  # End of day
```

---

## 🔧 Technical Differences

### Data Volume

```
Individual Contracts (Daily):
  28 instruments × ~55 bars each = ~1,540 total bars
  
Daily Continuous:
  1 instrument × 416 bars = 416 total bars
  
Hourly Continuous:
  1 instrument × 393 bars = 393 total bars
  BUT covers only ~56 trading days (393/7)
```

### Storage Size

| Type | Catalog Size | Metadata | Total |
|------|-------------|----------|-------|
| Individual | ~2.5 MB | ~500 KB | ~3 MB |
| Daily Continuous | ~180 KB | ~90 KB | ~270 KB |
| Hourly Continuous | ~170 KB | ~80 KB | ~250 KB |

### Processing Speed

```
Backtest Performance (approximate):

Individual Contracts:
  ⏱️ ~2-3 seconds (28 instruments)
  
Daily Continuous:
  ⏱️ ~0.5 seconds (single instrument)
  
Hourly Continuous:
  ⏱️ ~0.6 seconds (more bars but simpler)
```

---

## 📊 Feature Availability

| Feature | Individual | Daily Continuous | Hourly Continuous |
|---------|-----------|------------------|-------------------|
| **Open Interest** | ✅ Available | ✅ Available | ❌ **Not Available** |
| **Intraday Prices** | ❌ Daily only | ❌ Daily only | ✅ **Hourly bars** |
| **Expiry Dates** | ✅ Real expiry | ⚠️ Synthetic (2035) | ⚠️ Synthetic (2035) |
| **Multiple Contracts** | ✅ Yes | ❌ Single | ❌ Single |
| **Roll Costs** | ✅ Can simulate | ❌ Not included | ❌ Not included |
| **Date Filtering** | ❌ Not implemented | ✅ Available | ✅ **Will be available** |
| **Historical Depth** | 6 months (2023) | 20 months (2024-2025) | 3 months (Jun-Sep 2025) |

---

## 💡 Key Insights

### 1. Open Interest (OI) Availability

**Individual Contracts:**
```
Entry OI: 8,833,800
Exit OI:  9,081,600
Change:   +247,800 (bullish signal)
```

**Daily Continuous:**
```
Entry OI: 12,209,500
Exit OI:  11,165,700
Change:   -1,043,800 (bearish signal)
```

**Hourly Continuous:**
```
❌ NO OI DATA AVAILABLE
Cannot analyze OI changes
Must rely on price/volume only
```

### 2. Timeframe Capabilities

**Individual & Daily Continuous:**
- ✅ Swing trading (days to weeks)
- ✅ Position trading (weeks to months)
- ❌ Intraday trading (need hourly data)
- ❌ Scalping (need tick/minute data)

**Hourly Continuous:**
- ❌ Swing trading (insufficient history)
- ❌ Position trading (only 3 months)
- ✅ **Intraday trading** (perfect for this!)
- ⚠️ Scalping (1-hour bars may be too coarse)

### 3. Strategy Testing Scenarios

**Test Multi-Month Trend Following?**
- ✅ Daily Continuous (best choice)
- ⚠️ Individual Contracts (handle rolls)
- ❌ Hourly Continuous (not enough history)

**Test Intraday Breakout?**
- ❌ Daily Continuous (no intraday data)
- ❌ Individual Contracts (no intraday data)
- ✅ **Hourly Continuous (perfect!)**

**Test Expiry Week Behavior?**
- ✅ **Individual Contracts (best choice)**
- ❌ Daily Continuous (no expiry awareness)
- ❌ Hourly Continuous (no expiry awareness)

**Test OI-Based Strategies?**
- ✅ Individual Contracts (has OI)
- ✅ Daily Continuous (has OI)
- ❌ **Hourly Continuous (NO OI!)**

---

## 🎓 Learning from Each Type

### What Individual Contracts Teach You

```python
Lessons:
✓ Real market microstructure
✓ Rollover impact on P&L
✓ How liquidity migrates near expiry
✓ Calendar spread opportunities
✓ Risk of holding through expiry

Example Insight:
"Jun contract OI dropped 80% in last 5 days before expiry"
"Jul contract OI increased as traders rolled positions"
```

### What Daily Continuous Teaches You

```python
Lessons:
✓ Long-term trend behavior
✓ Multi-year strategy performance
✓ Drawdown management over time
✓ Seasonal patterns
✓ Overall market direction

Example Insight:
"Strategy made -590 points over 20 months"
"Win rate 37.8% but R:R ratio needs improvement"
"Max drawdown 15.77% occurred during Aug 2024 volatility"
```

### What Hourly Continuous Teaches You

```python
Lessons:
✓ Intraday volatility patterns
✓ Best trading hours (e.g., 09:15-10:15 most volatile)
✓ Within-day mean reversion
✓ Time-of-day effects
✓ Volume distribution across hours

Example Insight:
"First hour (09:15) has 3x volume vs last hour (15:15)"
"Price tends to reverse near 12:15 (lunch hour)"
"Best entry signals at 10:15 after opening volatility settles"
```

---

## 📝 Data Quality Comparison

### Completeness

**Individual Contracts:**
```
✅ All fields present
✅ OI data complete
⚠️ IV field empty (common for futures)
✅ No missing dates
```

**Daily Continuous:**
```
✅ All OHLCV present
✅ OI data complete
✅ No missing dates
⚠️ Split date format (quirk)
```

**Hourly Continuous:**
```
✅ All OHLCV present
❌ NO OI data
✅ No missing hours (within trading day)
⚠️ Only recent data (3 months)
```

### Data Gaps

**Individual Contracts:**
- No gaps within each contract
- Natural gaps between non-overlapping expiries

**Daily Continuous:**
- No gaps (continuous series)
- Holidays excluded (market closed days)

**Hourly Continuous:**
- No gaps within trading hours
- Natural gaps: 15:15 → next day 09:15
- Weekend gaps: Friday 15:15 → Monday 09:15

---

## 🔄 Conversion Process Differences

### Individual Contracts → Catalog

```python
Process:
1. Read CSV with EXPIRY_DT
2. Group by expiry date
3. Create one instrument per expiry
4. Build bars for each instrument
5. Result: 28 instruments in catalog
```

### Daily Continuous → Catalog

```python
Process:
1. Read CSV (merge split date columns)
2. Parse DD-MM-YYYY format
3. Create single CONTINUOUS instrument
4. Build all bars for one instrument
5. Result: 1 instrument with 416 bars
```

### Hourly Continuous → Catalog

```python
Process:
1. Read CSV (combine date + time)
2. Parse DD-MM-YYYY + HH:MM:SS
3. Create single CONTINUOUS instrument
4. Build all bars for one instrument
5. Result: 1 instrument with 393 hourly bars
```

---

## 🚀 Performance Comparison

### Backtest Execution Time

```
Strategy: ND_TT_V4
Hardware: Standard laptop

Individual Contracts (28 instruments):
├── Data loading: ~0.8s
├── Strategy execution: ~1.5s
├── Report generation: ~0.5s
└── Total: ~2.8s

Daily Continuous (1 instrument, 416 bars):
├── Data loading: ~0.2s
├── Strategy execution: ~0.2s
├── Report generation: ~0.1s
└── Total: ~0.5s

Hourly Continuous (1 instrument, 393 bars):
├── Data loading: ~0.2s
├── Strategy execution: ~0.2s
├── Report generation: ~0.1s
└── Total: ~0.5s
```

### Memory Usage

```
Individual Contracts:
  Peak RAM: ~150 MB

Daily Continuous:
  Peak RAM: ~80 MB

Hourly Continuous:
  Peak RAM: ~85 MB
```

---

## 📌 Summary

### Quick Decision Guide

**Choose Individual Contracts if:**
- ✅ You need realistic expiry handling
- ✅ Testing rollover strategies
- ✅ Studying OI behavior near expiry
- ✅ Want to understand contract lifecycle

**Choose Daily Continuous if:**
- ✅ Long-term trend testing (months/years)
- ✅ Daily timeframe strategies
- ✅ Need OI data for analysis
- ✅ Want simple single-instrument backtest

**Choose Hourly Continuous if:**
- ✅ **Intraday/day trading strategies**
- ✅ Testing time-of-day patterns
- ✅ Scalping or hourly breakouts
- ✅ Don't need OI data
- ⚠️ Okay with limited history (3 months)

---

## 🎯 Your Hourly Data Specifics

**File:** `NIFTY_FUT_hourly_data.csv`

**Coverage:**
- Start: June 27, 2025 (09:15)
- End: September 16, 2025 (15:15)
- Duration: ~80 calendar days, ~56 trading days
- Total: 393 hourly bars

**Trading Hours:**
```
09:15 - Opening hour (high volume)
10:15 - Post-opening
11:15 - Mid-morning
12:15 - Lunch hour (low volume typically)
13:15 - Post-lunch
14:15 - Late afternoon
15:15 - Closing hour
```

**Missing Fields:**
- ❌ No OI (Open Interest)
- ❌ No IV (Implied Volatility)
- ✅ Has Volume
- ✅ Complete OHLC

**Best Use Case:**
```python
# Intraday breakout strategy
# First hour breakout continuation
# End-of-day reversal patterns
# Time-weighted strategies
```

---

**Next Steps:** See `HOURLY_BACKTEST_SETUP.md` for implementation details!

