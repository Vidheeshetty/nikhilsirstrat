# Paper Trading Folder Structure

## Overview

Paper trading logs are now organized date-wise to match the backtesting folder structure, making it easier to manage and locate trading sessions.

## New Structure

```
runlogs/papertrading/
├── YYYY-MM-DD/                    # Date folders
│   ├── HH-MM-SS_strategy_name/    # Session folders with timestamp and strategy
│   │   ├── session_data.json      # Session metadata
│   │   ├── live_data.json         # Real-time performance data
│   │   ├── orders.csv             # Order history
│   │   ├── positions.csv          # Position history
│   │   ├── trades.csv             # Trade history
│   │   └── report.html            # HTML report
│   └── HH-MM-SS_strategy_name/    # Additional sessions for the same date
└── YYYY-MM-DD/                    # Additional date folders
```

## Example Structure

```
runlogs/papertrading/
├── 2025-07-01/
│   ├── 09-30-15_smafractalscalper/
│   ├── 14-45-22_trendridingstrategy/
│   └── 16-20-08_swingrangeexpansion/
├── 2025-07-02/
│   ├── 09-15-33_smafractalscalper/
│   └── 13-22-45_trendridingstrategy/
└── 2025-07-03/
    └── 10-05-12_smafractalscalper/
```

## Comparison with Previous Structure

### Before (Old Structure)
```
runlogs/papertrading/
├── 20250701_093015/    # YYYYMMDD_HHMMSS (no strategy name)
├── 20250701_144522/
├── 20250702_091533/
└── 20250703_100512/
```

### After (New Structure)
```
runlogs/papertrading/
├── 2025-07-01/         # YYYY-MM-DD (readable date)
│   ├── 09-30-15_smafractalscalper/    # HH-MM-SS_strategy_name
│   └── 14-45-22_trendridingstrategy/
├── 2025-07-02/
│   └── 09-15-33_smafractalscalper/
└── 2025-07-03/
    └── 10-05-12_smafractalscalper/
```

## Benefits

1. **Date Organization**: Easy to find sessions by date
2. **Strategy Identification**: Strategy name in folder makes it clear what was running
3. **Consistency**: Matches backtesting folder structure
4. **Readability**: Human-readable dates (YYYY-MM-DD vs YYYYMMDD)
5. **Scalability**: Better organization for multiple strategies per day

## Implementation Details

### Strategy Name Extraction

The strategy name is extracted from the paper trading configuration:

1. **From `strategies` section**: Uses the first enabled strategy key
2. **From `strategy_name` field**: Direct strategy name specification
3. **Fallback**: Uses "unknown_strategy" if no strategy is found

### Code Changes

- **`utils/reporting/paper_trading_reporter.py`**: Updated session directory creation
- **`scripts/paper_trading/paper_trading_server.py`**: Updated session discovery logic

### Backward Compatibility

The paper trading server automatically handles both old and new folder structures when looking for sessions, ensuring existing data remains accessible.

## Migration

No manual migration is required. New sessions will automatically use the new structure while old sessions remain accessible in their original format. 