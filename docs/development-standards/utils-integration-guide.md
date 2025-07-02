# Utils Integration Guide

This document provides guidance on integrating strategy modules with the utils package to maximize code reuse and maintain consistency across strategies.

## Overview

The `utils.strategy` package provides common functionality that can be leveraged by all strategies. This guide identifies integration opportunities and provides migration patterns for existing strategies.

## Available Utils Modules

### 1. `utils.strategy.enums`

**Purpose**: Common enums used across strategies

**Available Enums:**
- `Direction` - Trade direction (LONG/SHORT/NONE)
- `ExitReason` - Exit reasons (STOP_LOSS/TAKE_PROFIT/TIME_LIMIT/REVERSAL/NONE)
- `OrderSide` - Order sides (BUY/SELL)

**Migration Pattern:**
```python
# Before (strategy-specific enum)
class Direction(Enum):
    NONE = "NONE"
    LONG = "LONG"
    SHORT = "SHORT"

# After (utils integration)
from utils.strategy import Direction
```

### 2. `utils.strategy.position`

**Purpose**: Position sizing calculations

**Available Functions:**
- `calculate_risk_based_size()` - Size based on risk amount and stop distance
- `calculate_fixed_size()` - Size based on capital percentage
- `calculate_percentage_based_size()` - Size based on percentage stop loss

**Migration Pattern:**
```python
# Before (strategy-specific implementation)
def calculate_size(capital, risk_pct, entry_price, stop_price):
    risk_per_unit = abs(entry_price - stop_price)
    total_risk = capital * risk_pct
    return int(total_risk / risk_per_unit)

# After (utils integration)
from utils.strategy.position import calculate_risk_based_size

def calculate_size(capital, risk_pct, entry_price, stop_price):
    return calculate_risk_based_size(capital, risk_pct, entry_price, stop_price)
```

### 3. `utils.strategy.risk`

**Purpose**: Risk management calculations

**Available Functions:**
- `calculate_stop_target_prices_percentage()` - Percentage-based levels
- `calculate_stop_target_prices_fixed()` - Fixed amount levels  
- `calculate_stop_target_prices_rr()` - Risk-reward ratio levels
- `is_stop_hit()`, `is_target_hit()` - Level checking
- `calculate_pnl()` - P&L calculation

**Migration Pattern:**
```python
# Before (strategy-specific implementation)
def compute_exit_prices(entry_price, direction, range_val, target_rr, stop_rr):
    if direction == Direction.LONG:
        target_price = entry_price + target_rr * range_val
        stop_price = entry_price - stop_rr * range_val
    # ... more logic
    return target_price, stop_price

# After (utils integration)
from utils.strategy.risk import calculate_stop_target_prices_rr

def compute_exit_prices(entry_price, direction, range_val, target_rr, stop_rr):
    return calculate_stop_target_prices_rr(
        entry_price, direction, range_val, stop_rr, target_rr
    )
```

### 4. `utils.strategy.trades`

**Purpose**: Trade record structures and utilities

**Available Classes/Functions:**
- `TradeRecord` - Standard trade record dataclass
- `calculate_trade_metrics()` - Performance metrics calculation
- `trades_to_dict_list()` - Conversion utilities
- `enrich_trades_with_cumulative_pnl()` - Add cumulative P&L

**Migration Pattern:**
```python
# Before (strategy-specific trade record)
@dataclass
class TradeRecord:
    instrument: str
    entry_date: str
    trade_type: str
    entry_price: float
    # ... more fields

# After (utils integration)
from utils.strategy import TradeRecord, Direction, ExitReason

# Use standard TradeRecord with Direction and ExitReason enums
trade = TradeRecord(
    instrument="NIFTY",
    entry_date="2025-01-01",
    entry_price=18000.0,
    exit_date="2025-01-02", 
    exit_price=18100.0,
    direction=Direction.LONG,
    exit_reason=ExitReason.TAKE_PROFIT
)
```

### 5. `utils.strategy.indicators`

**Purpose**: Technical analysis functions

**Available Functions:**
- `sma()` - Simple Moving Average
- `ema()` - Exponential Moving Average

**Extension Opportunities:**
- Add more indicators as needed by strategies
- Contribute common calculations back to utils

## Integration Opportunities by Strategy Module

### entry.py Integration

**High Priority:**
1. Use `Direction` enum from utils.strategy.enums
2. Leverage `sma()`, `ema()` from utils.strategy.indicators for signal computation

**Medium Priority:**
3. Move common signal computation patterns to utils.strategy.indicators

**Example:**
```python
# Before
from enum import Enum

class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"

def compute_signal(...):
    # Signal logic
    return Direction.LONG, entry_price

# After
from utils.strategy import Direction
from utils.strategy.indicators import sma

def compute_signal(...):
    # Use utils functions
    trend = sma(prices, 20)
    # Signal logic
    return Direction.LONG, entry_price
```

### exit.py Integration

**High Priority:**
1. Use `ExitReason` enum from utils.strategy.enums
2. Use risk management functions from utils.strategy.risk

**Example:**
```python
# Before
class ExitReason:
    STOP_LOSS = "SL"
    TAKE_PROFIT = "TP"

def should_exit(...):
    if current_price <= stop_price:
        return True, ExitReason.STOP_LOSS, stop_price

# After
from utils.strategy import ExitReason, Direction
from utils.strategy.risk import is_stop_hit

def should_exit(...):
    if is_stop_hit(current_price, entry_price, direction, stop_pct):
        return True, ExitReason.STOP_LOSS, stop_price
```

### risk.py Integration

**High Priority:**
1. Use calculation functions from utils.strategy.risk
2. Use `Direction` enum from utils.strategy.enums

**Example:**
```python
# Before
class RiskManager:
    def get_exit_prices(self, entry_price, direction, range_val):
        if direction == Direction.LONG:
            stop_price = entry_price - self.stop_rr * range_val
            target_price = entry_price + self.target_rr * range_val
        # ... more logic

# After
from utils.strategy import Direction
from utils.strategy.risk import calculate_stop_target_prices_rr

class RiskManager:
    def get_exit_prices(self, entry_price, direction, range_val):
        return calculate_stop_target_prices_rr(
            entry_price, direction, range_val, self.stop_rr, self.target_rr
        )
```

### position.py Integration

**High Priority:**
1. Use position sizing functions from utils.strategy.position

**Example:**
```python
# Before
def calculate_size(capital, risk_pct, entry_price, stop_price):
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0:
        return 1
    total_risk = capital * risk_pct
    size = int(total_risk / risk_per_unit)
    return max(size, 1)

# After
from utils.strategy.position import calculate_risk_based_size

def calculate_size(capital, risk_pct, entry_price, stop_price):
    return calculate_risk_based_size(capital, risk_pct, entry_price, stop_price)
```

### strategy.py Integration

**High Priority:**
1. Use `TradeRecord` from utils.strategy.trades
2. Use `Direction`, `ExitReason` from utils.strategy.enums
3. Use `calculate_pnl` from utils.strategy.risk

**Example:**
```python
# Before
@dataclass
class TradeRecord:
    instrument: str
    entry_price: float
    # ... custom fields

def _exit_trade(self, price, reason):
    pnl = price - self._entry_price
    if self._position_side == Direction.SHORT:
        pnl = -pnl

# After
from utils.strategy import TradeRecord, Direction, ExitReason
from utils.strategy.risk import calculate_pnl

def _exit_trade(self, price, reason):
    pnl = calculate_pnl(
        self._entry_price, price, self._position_side, self._position_size
    )
    
    trade = TradeRecord(
        instrument=self.config.instrument_id,
        entry_date=str(self._entry_index),
        entry_price=self._entry_price,
        exit_date=str(self._current_index),
        exit_price=price,
        direction=self._position_side,
        exit_reason=ExitReason.STOP_LOSS  # or appropriate reason
    )
```

## Migration Strategy

### Phase 1: High Priority (Immediate)
1. Replace custom enums with utils.strategy.enums
2. Replace custom trade records with utils.strategy.trades.TradeRecord
3. Use utils.strategy.risk functions for common calculations

### Phase 2: Medium Priority (Next Sprint)
1. Migrate position sizing to utils.strategy.position functions
2. Use utils.strategy.indicators for technical analysis
3. Consolidate common patterns into utils

### Phase 3: Low Priority (Future)
1. Identify additional utils opportunities
2. Contribute new utilities back to utils package
3. Optimize performance of utils functions

## Best Practices

### 1. Check Utils First
Before implementing any common functionality, check if it exists in utils:
```python
# Good
from utils.strategy import Direction, calculate_pnl

# Avoid
class Direction(Enum):  # Duplicates utils functionality
    LONG = "LONG"
```

### 2. Maintain Strategy Independence
Use utils functions but allow strategy-specific customization:
```python
# Good - uses utils but allows customization
def calculate_size(capital, risk_pct, entry_price, stop_price, min_size=1):
    size = calculate_risk_based_size(capital, risk_pct, entry_price, stop_price)
    return max(size, min_size)  # Strategy-specific minimum

# Avoid - too rigid
def calculate_size(capital, risk_pct, entry_price, stop_price):
    return calculate_risk_based_size(capital, risk_pct, entry_price, stop_price)
```

### 3. Document Deviations
When you can't use utils functions, document why:
```python
def custom_exit_logic(...):
    """Custom exit logic specific to this strategy.
    
    Note: Cannot use utils.strategy.risk.is_stop_hit() because this strategy
    uses time-weighted stop losses that require custom implementation.
    """
    pass
```

### 4. Contribute Back
If you create reusable functionality, consider adding it to utils:
```python
# If this pattern is used across strategies, propose adding to utils
def calculate_volatility_adjusted_size(...):
    """Position sizing adjusted for volatility - candidate for utils."""
    pass
```

## Testing Utils Integration

### Unit Tests
Test that utils integration works correctly:
```python
def test_direction_enum_integration():
    from utils.strategy import Direction
    assert Direction.LONG.value == "LONG"

def test_trade_record_integration():
    from utils.strategy import TradeRecord, Direction, ExitReason
    trade = TradeRecord(
        instrument="TEST",
        entry_date="2025-01-01",
        entry_price=100.0,
        exit_date="2025-01-02",
        exit_price=105.0,
        direction=Direction.LONG,
        exit_reason=ExitReason.TAKE_PROFIT
    )
    assert trade.pnl == 5.0
```

### Integration Tests
Test strategy modules work together with utils:
```python
def test_strategy_with_utils_integration():
    # Test that strategy works with utils-integrated modules
    pass
```

## Performance Considerations

### Utils Function Performance
- Utils functions are optimized for common use cases
- Profile strategy performance before and after utils integration
- Report performance issues with utils functions

### Memory Usage
- Utils functions avoid unnecessary data copying
- Use utils functions for bulk operations when possible

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure utils.strategy is properly installed
2. **Enum Compatibility**: Check that enum values match expected formats
3. **Type Mismatches**: Verify function signatures match utils expectations

### Migration Checklist

- [ ] Replace custom enums with utils.strategy.enums
- [ ] Update trade records to use utils.strategy.trades.TradeRecord
- [ ] Migrate risk calculations to utils.strategy.risk functions
- [ ] Update position sizing to use utils.strategy.position functions
- [ ] Test all imports work correctly
- [ ] Verify strategy behavior unchanged after migration
- [ ] Update tests to reflect utils integration
- [ ] Update documentation

---

*This guide ensures maximum code reuse while maintaining strategy independence and flexibility.* 