# CSV to Parquet Conversion - Format Changes Explained

## 📊 Your CSV Format vs Standard Format

### Your Continuous Futures CSV Format
```csv
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,22138,21964.7,22029.5,5160750,12209500
17-01-2024,00:00:00+05:30,21743.7,21854.75,21563.3,21589.55,11483200,11165700
```

**Issues with this format:**
1. ✗ Date and time split across TWO columns (unusual!)
2. ✗ Date format is DD-MM-YYYY (not standard YYYY-MM-DD)
3. ✗ Time has timezone info (+05:30)
4. ✗ Empty column name between date and open
5. ✗ No EXPIRY_DT column (continuous contract)

### Standard Expiry-Based CSV Format
```csv
SYMBOL,DATE,EXPIRY_DT,OPEN,HIGH,LOW,CLOSE,OI,IV
NIFTY,2023-06-01,2023-06-29,18624.95,18659.0,18550.0,18570.0,8833800,
NIFTY,2023-06-01,2023-07-27,18702.0,18735.0,18633.8,18650.35,741950,
```

**Standard format:**
1. ✓ Single DATE column
2. ✓ Date format is YYYY-MM-DD
3. ✓ Has EXPIRY_DT for each contract
4. ✓ Clear column names
5. ✓ Symbol identifier

---

## 🔧 Key Changes Made to Handle Your Format

### Change 1: CSV Loading with Column Merging

**Original Code** (from `csv_to_parquet_converter.py`):
```python
def load_csv(cfg: ConverterConfig) -> pd.DataFrame:
    # ... file finding logic ...
    
    for path in csv_paths:
        df = pd.read_csv(path)
        if "DATE" not in df.columns:
            logger.warning("Missing DATE column – skipped")
            continue
        df["DATE"] = pd.to_datetime(df["DATE"], utc=True)  # Simple conversion
        frames.append(df)
    
    df_all = pd.concat(frames, ignore_index=True).sort_values("DATE")
    return df_all
```

**New Code** (for continuous futures):
```python
def load_continuous_csv(csv_path: str) -> pd.DataFrame:
    logger.info("📖 Reading %s", csv_path)
    
    df = pd.read_csv(csv_path)
    
    # ⭐ CHANGE 1: Combine split date columns
    if 'date' in df.columns and df.columns[1] == 'Unnamed: 1':
        # Combine date and time columns
        df['DATE'] = df['date'].astype(str) + ' ' + df['Unnamed: 1'].astype(str)
        # Drop the original columns
        df = df.drop(['date', 'Unnamed: 1'], axis=1)
    elif 'date' in df.columns:
        df['DATE'] = df['date']
        df = df.drop(['date'], axis=1)
    
    # ⭐ CHANGE 2: Rename lowercase columns to uppercase
    column_map = {
        'open': 'OPEN',
        'high': 'HIGH', 
        'low': 'LOW',
        'close': 'CLOSE',
        'volume': 'VOLUME',
        'oi': 'OI'
    }
    df = df.rename(columns=column_map)
    
    # ⭐ CHANGE 3: Custom date parser for DD-MM-YYYY format
    def parse_date(date_str):
        try:
            # Remove timezone info for parsing
            date_part = str(date_str).split('+')[0].strip()
            # Parse DD-MM-YYYY format specifically
            if '-' in date_part and len(date_part.split('-')[0]) <= 2:
                dt = pd.to_datetime(date_part, format='%d-%m-%Y %H:%M:%S')
            else:
                dt = pd.to_datetime(date_part)
            return dt.tz_localize('UTC')
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return pd.NaT
    
    df['DATE'] = df['DATE'].apply(parse_date)
    df = df.dropna(subset=['DATE'])
    df = df.sort_values('DATE').reset_index(drop=True)
    
    logger.info("✅ Loaded %d rows from %s to %s", 
                len(df), df['DATE'].min(), df['DATE'].max())
    
    return df
```

**What Changed:**
1. ✅ Detects split date columns (`'date'` and `'Unnamed: 1'`)
2. ✅ Merges them into single `DATE` column
3. ✅ Converts lowercase column names to uppercase
4. ✅ Custom date parser handles DD-MM-YYYY format
5. ✅ Strips timezone info before parsing
6. ✅ Validates and reports date range

---

### Change 2: Continuous Contract Creation (No Expiry)

**Original Code** (expiry-based):
```python
def build_instrument(cfg: ConverterConfig, expiry_str: str) -> FuturesContract:
    """Create unique FuturesContract with specific expiry date."""
    
    # Convert expiry string to datetime
    expiry_clean = str(expiry_str).split(" ")[0]
    expiry_dt = datetime.strptime(expiry_clean, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    ) + timedelta(hours=23, minutes=59)
    
    # ⭐ Symbol includes expiry date
    symbol_with_expiry = f"{cfg.symbol}{expiry_dt.strftime('%Y%m%d')}.FUT"
    # Example: NIFTY20230629.FUT
    
    iid = InstrumentId(symbol=Symbol(symbol_with_expiry), venue=Venue(cfg.venue))
    
    instrument = FuturesContract(
        instrument_id=iid,
        raw_symbol=Symbol(symbol_with_expiry),
        # ...
        expiration_ns=dt_to_unix_nanos(expiry_dt),  # ⭐ Real expiry
        # ...
    )
    return instrument
```

**New Code** (continuous contract):
```python
def build_continuous_instrument(cfg: ConverterConfig) -> FuturesContract:
    """Create synthetic continuous futures contract."""
    
    # ⭐ Symbol marked as CONTINUOUS
    symbol_str = f"{cfg.symbol}_CONTINUOUS.FUT"
    # Example: NIFTY_CONTINUOUS.FUT
    
    iid = InstrumentId(symbol=Symbol(symbol_str), venue=Venue(cfg.venue))
    
    now_utc = datetime.now(timezone.utc)
    # ⭐ Set expiry far in future (10 years) - not a real expiry
    expiry_dt = datetime(2035, 12, 31, 23, 59, tzinfo=timezone.utc)
    
    instrument = FuturesContract(
        instrument_id=iid,
        raw_symbol=Symbol(symbol_str),
        asset_class=AssetClass.INDEX,
        currency=Currency.from_str("INR"),
        price_precision=cfg.price_precision,
        price_increment=Price(cfg.price_increment, cfg.price_precision),
        multiplier=Quantity(cfg.multiplier, 0),
        lot_size=Quantity(1, 0),
        underlying=f"{cfg.symbol}.{cfg.venue}.INDEX",
        activation_ns=0,
        expiration_ns=dt_to_unix_nanos(expiry_dt),  # ⭐ Synthetic expiry
        ts_event=dt_to_unix_nanos(now_utc),
        ts_init=dt_to_unix_nanos(now_utc),
        exchange=cfg.venue,
    )
    logger.info("🛠️  Built Continuous FuturesContract %s", instrument.id)
    return instrument
```

**What Changed:**
1. ✅ No expiry date parameter needed
2. ✅ Symbol includes `_CONTINUOUS` marker
3. ✅ Synthetic expiry set to 2035 (far future)
4. ✅ Creates SINGLE instrument, not multiple
5. ✅ Result: `NIFTY_CONTINUOUS.FUT.NSE`

---

### Change 3: Main Conversion Logic

**Original Code** (expiry-based):
```python
def run_conversion(cfg: ConverterConfig):
    clear_catalog_dirs(cfg)
    df = load_csv(cfg)
    
    # ⭐ Requires EXPIRY_DT column
    if "EXPIRY_DT" not in df.columns or df["EXPIRY_DT"].isna().all():
        raise ValueError("CSV must contain EXPIRY_DT column")
    
    instruments: list[FuturesContract] = []
    all_bars: list[Bar] = []
    all_meta_frames: list[pd.DataFrame] = []
    
    # ⭐ Group by expiry and create multiple instruments
    for expiry_str, df_slice in df.groupby("EXPIRY_DT"):
        instrument = build_instrument(cfg, expiry_str)
        instruments.append(instrument)
        
        bars = build_bars(df_slice, instrument.id, cfg.bar_interval, cfg.price_precision)
        all_bars.extend(bars)
        
        meta_df = build_bar_metadata(df_slice, str(instrument.id), cfg.extra_meta_fields)
        all_meta_frames.append(meta_df)
    
    write_catalog(cfg, instruments, all_bars)
    # ...
```

**New Code** (continuous):
```python
def run_conversion(cfg: ConverterConfig):
    if cfg.data_kind != "bar":
        raise NotImplementedError("Only bar data conversion is implemented")
    
    clear_catalog_dirs(cfg)
    
    # ⭐ Load continuous CSV (no EXPIRY_DT needed)
    df = load_continuous_csv(cfg.source_csv)
    
    # ⭐ Build SINGLE continuous instrument
    instrument = build_continuous_instrument(cfg)
    
    # ⭐ Build bars for ALL data (no grouping by expiry)
    bars = build_bars(df, instrument.id, cfg.bar_interval, cfg.price_precision)
    
    # ⭐ Write single instrument to catalog
    write_catalog(cfg, instrument, bars)
    
    # Build and write metadata
    bar_meta_df = build_bar_metadata(df, str(instrument.id), cfg.extra_meta_fields)
    write_meta(cfg, instrument, bar_meta_df)
    
    logger.info(
        "🎉 Conversion complete: %d bars for continuous contract %s",
        len(bars),
        instrument.id
    )
    # ...
```

**What Changed:**
1. ✅ No EXPIRY_DT column required
2. ✅ No grouping by expiry
3. ✅ Single instrument created
4. ✅ All bars belong to one instrument
5. ✅ Simpler flow (no loops)

---

## 📋 Step-by-Step: What Happens to Your Data

### Input (Your CSV):
```
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,22138,21964.7,22029.5,5160750,12209500
```

### Step 1: Column Merging
```python
# Before
columns: ['date', 'Unnamed: 1', 'open', 'high', 'low', 'close', 'volume', 'oi']

# After combining
df['DATE'] = '16-01-2024' + ' ' + '00:00:00+05:30'
df['DATE'] = '16-01-2024 00:00:00+05:30'
```

### Step 2: Date Parsing
```python
date_str = '16-01-2024 00:00:00+05:30'

# Remove timezone
date_part = '16-01-2024 00:00:00'

# Parse with DD-MM-YYYY format
dt = pd.to_datetime('16-01-2024 00:00:00', format='%d-%m-%Y %H:%M:%S')
# Result: 2024-01-16 00:00:00

# Convert to UTC
dt_utc = dt.tz_localize('UTC')
# Result: 2024-01-16 00:00:00+00:00
```

### Step 3: Column Renaming
```python
# Before
columns: ['DATE', 'open', 'high', 'low', 'close', 'volume', 'oi']

# After
columns: ['DATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME', 'OI']
```

### Step 4: Instrument Creation
```python
# Single continuous contract
instrument_id = "NIFTY_CONTINUOUS.FUT.NSE"
expiry = 2035-12-31 (synthetic, far future)
```

### Step 5: Bar Creation
```python
# All 416 rows become bars for the single instrument
bars = [
    Bar(NIFTY_CONTINUOUS.FUT.NSE, 2024-01-16, O:22089.9, H:22138, L:21964.7, C:22029.5),
    Bar(NIFTY_CONTINUOUS.FUT.NSE, 2024-01-17, O:21743.7, H:21854.75, L:21563.3, C:21589.55),
    # ... 414 more bars
]
```

### Output: Nautilus Catalog
```
catalog-data/nifty-continuous-yf/catalog/
├── instrument.parquet  (1 instrument: NIFTY_CONTINUOUS.FUT.NSE)
└── bar.parquet         (416 bars, all for same instrument)

catalog-data/nifty-continuous-yf/catalog-meta/
├── instruments.parquet (metadata: strike, expiry, etc.)
└── bar_metadata.parquet (OI and VOLUME for each bar)
```

---

## 🔍 Comparison Table

| Feature | Original Converter | Continuous Converter |
|---------|-------------------|---------------------|
| **CSV Format** | Standard DATE column | Split date,time columns |
| **Date Format** | YYYY-MM-DD | DD-MM-YYYY |
| **Timezone** | Already UTC | Needs stripping (+05:30) |
| **Column Names** | Uppercase | Lowercase (need mapping) |
| **EXPIRY_DT** | Required | Not present |
| **Instruments Created** | Multiple (one per expiry) | Single continuous |
| **Symbol Format** | NIFTY20230629.FUT | NIFTY_CONTINUOUS.FUT |
| **Grouping** | Group by expiry date | No grouping |
| **Use Case** | Realistic expiry handling | Long-term trend analysis |

---

## 💡 Why These Changes Were Necessary

### Problem 1: Split Date Columns
**Your CSV:**
```
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,...
```

**Why it's unusual:** The date and time are in separate columns with an empty column name between them. This creates `'Unnamed: 1'` when pandas reads it.

**Solution:** Detect and merge these columns before processing.

### Problem 2: DD-MM-YYYY Format
**Your CSV:** `16-01-2024`  
**Standard:** `2024-01-16`

**Why it matters:** Python's default datetime parser expects ISO format (YYYY-MM-DD). Your format would be parsed as "16th day of January" incorrectly if using wrong format.

**Solution:** Use explicit format string `'%d-%m-%Y %H:%M:%S'` for parsing.

### Problem 3: Timezone Info
**Your CSV:** `00:00:00+05:30` (IST timezone)  
**Nautilus needs:** UTC timezone

**Why it matters:** All Nautilus timestamps must be in UTC for consistency.

**Solution:** Strip `+05:30` before parsing, then localize to UTC.

### Problem 4: No Expiry Dates
**Your CSV:** Continuous contract (no EXPIRY_DT column)  
**Standard:** Multiple contracts with different expiries

**Why it matters:** Original converter requires EXPIRY_DT to create separate instruments.

**Solution:** Create single instrument with synthetic far-future expiry.

---

## 🧪 Testing Your Format

### Test Input
```csv
date,,open,high,low,close,volume,oi
16-01-2024,00:00:00+05:30,22089.9,22138,21964.7,22029.5,5160750,12209500
```

### Test Output (Parsed DataFrame)
```python
DATE                           OPEN     HIGH      LOW       CLOSE    VOLUME     OI
2024-01-16 00:00:00+00:00   22089.9  22138.0  21964.7  22029.5   5160750  12209500
```

### Test Output (Nautilus Bar)
```python
Bar(
    bar_type=BarType('NIFTY_CONTINUOUS.FUT.NSE-1-DAY-LAST-EXTERNAL'),
    open=Price(22089.90, 2),
    high=Price(22138.00, 2),
    low=Price(21964.70, 2),
    close=Price(22029.50, 2),
    volume=Quantity(5160750, 0),
    ts_event=1705363200000000000,  # 2024-01-16 00:00:00 UTC in nanoseconds
    ts_init=1705363200000000000
)
```

---

## 📝 Configuration Differences

### Original Config (Expiry-Based)
```yaml
source_csv: "raw-data/source=NSER/.../NIFTY_2023.csv"
# CSV has EXPIRY_DT column with values like "2023-06-29"
```

### New Config (Continuous)
```yaml
source_csv: "data/futures/YF/NIFTY_FUT_daily_data_continous.csv"
# CSV has NO EXPIRY_DT, uses lowercase columns, split date format
```

---

## ✅ Summary of All Changes

### Data Loading Changes
1. ✅ Merge split date/time columns
2. ✅ Convert lowercase to uppercase column names
3. ✅ Parse DD-MM-YYYY format
4. ✅ Strip timezone before parsing
5. ✅ Localize to UTC

### Instrument Creation Changes
1. ✅ Create single instrument (not multiple)
2. ✅ Add `_CONTINUOUS` to symbol
3. ✅ Use synthetic expiry (2035)
4. ✅ No grouping by expiry needed

### Workflow Changes
1. ✅ No EXPIRY_DT validation
2. ✅ No loop over expiry groups
3. ✅ Single metadata block
4. ✅ Simpler catalog structure

### Result
- **Input:** 416 rows in unusual CSV format
- **Output:** 1 instrument with 416 bars
- **Format:** Proper Nautilus Parquet catalog
- **Compatibility:** Works with existing backtest infrastructure

---

**Your continuous futures CSV format is now fully supported!** 🎉

