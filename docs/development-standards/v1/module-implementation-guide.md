# Module Implementation Guide

This document provides detailed implementation requirements for each module in the strategy framework.

## Core Modules

### 1. strategy.py - Main Strategy Class

**Requirements:**
- Must extend `utils.strategy.BaseStrategy`
- Implement required methods: `_setup()`, `on_quote()`, `on_stop()`
- Use modular components from other modules
- Include proper type hints and docstrings

**Utils Integration:**
- Import `Direction`, `ExitReason` from `utils.strategy.enums`
- Use `TradeRecord` from `utils.strategy.trades` for trade tracking
- Leverage `calculate_pnl` from `utils.strategy.risk` for P&L calculations

**Template:**
```python
from utils.strategy import BaseStrategy, Direction, TradeRecord
from .config import StrategyConfig
from .entry import compute_signal
from .exit import should_exit
from .risk import RiskManager
from .position import calculate_size

class MyStrategy(BaseStrategy):
    config_class = StrategyConfig
    
    def _setup(self) -> None:
        # Initialize strategy state
        super()._setup()
    
    def on_quote(self, price: float):
        # Main strategy logic
        pass
    
    def on_stop(self):
        # Cleanup
        super().on_stop()
```

### 2. config.py - Configuration Schema

**Requirements:**
- Use dataclass with type hints
- Include validation methods
- Support YAML serialization
- Document all parameters

**Template:**
```python
from dataclasses import dataclass

@dataclass
class StrategyConfig:
    instrument_id: str
    # Add strategy-specific parameters
    
    def validate(self) -> None:
        # Add validation logic
        pass
```

### 3. entry.py - Entry Signal Logic

**Requirements:**
- Stateless functions for signal computation
- Use `Direction` enum from `utils.strategy.enums`
- Include comprehensive docstrings
- Return structured signal information

**Utils Integration:**
- Import `Direction` from `utils.strategy.enums`
- Use common indicator functions from `utils.strategy.indicators`

**Template:**
```python
from utils.strategy import Direction
from typing import Tuple

def compute_signal(...) -> Tuple[Direction, float, ...]:
    # Signal computation logic
    return Direction.NONE, 0.0
```

### 4. exit.py - Exit Signal Logic

**Requirements:**
- Stateless functions for exit conditions
- Use `ExitReason` enum from `utils.strategy.enums`
- Handle multiple exit conditions (SL, TP, time)
- Return exit decision with reason and price

**Utils Integration:**
- Import `Direction`, `ExitReason` from `utils.strategy.enums`
- Use risk management functions from `utils.strategy.risk`

**Template:**
```python
from utils.strategy import Direction, ExitReason
from utils.strategy.risk import is_stop_hit, is_target_hit
from typing import Tuple

def should_exit(...) -> Tuple[bool, ExitReason, float]:
    # Exit logic using utils functions
    if is_stop_hit(...):
        return True, ExitReason.STOP_LOSS, stop_price
    # ... more conditions
    return False, ExitReason.NONE, 0.0
```

### 5. risk.py - Risk Management

**Requirements:**
- Risk assessment and position management
- Integration with utils risk functions
- Strategy-specific risk rules
- Clear interface for strategy class

**Utils Integration:**
- Use functions from `utils.strategy.risk` for common calculations
- Import `Direction` from `utils.strategy.enums`
- Leverage `calculate_stop_target_prices_*` functions

**Template:**
```python
from utils.strategy import Direction
from utils.strategy.risk import calculate_stop_target_prices_percentage

class RiskManager:
    def __init__(self, stop_pct: float, target_pct: float):
        self.stop_pct = stop_pct
        self.target_pct = target_pct
    
    def get_exit_prices(self, entry_price: float, direction: Direction):
        return calculate_stop_target_prices_percentage(
            entry_price, direction, self.stop_pct, self.target_pct
        )
```

### 6. position.py - Position Sizing

**Requirements:**
- Position size calculation logic
- Risk-based sizing algorithms
- Integration with utils position functions
- Strategy-specific customizations

**Utils Integration:**
- Use functions from `utils.strategy.position`
- Choose appropriate sizing method based on strategy needs

**Template:**
```python
from utils.strategy.position import calculate_risk_based_size

def calculate_size(capital: float, risk_pct: float, entry_price: float, stop_price: float) -> int:
    return calculate_risk_based_size(capital, risk_pct, entry_price, stop_price)
```

## Utils Integration Guidelines

### Available Utils Modules:

1. **`utils.strategy.enums`**
   - `Direction` - Trade direction (LONG/SHORT/NONE)
   - `ExitReason` - Exit reasons (STOP_LOSS/TAKE_PROFIT/TIME_LIMIT/etc.)
   - `OrderSide` - Order sides (BUY/SELL)

2. **`utils.strategy.position`**
   - `calculate_risk_based_size()` - Risk-based position sizing
   - `calculate_fixed_size()` - Fixed percentage sizing
   - `calculate_percentage_based_size()` - Percentage stop-based sizing

3. **`utils.strategy.risk`**
   - `calculate_stop_target_prices_percentage()` - Percentage-based levels
   - `calculate_stop_target_prices_fixed()` - Fixed amount levels
   - `calculate_stop_target_prices_rr()` - Risk-reward ratio levels
   - `is_stop_hit()`, `is_target_hit()` - Level checking functions
   - `calculate_pnl()` - P&L calculation

4. **`utils.strategy.trades`**
   - `TradeRecord` - Standard trade record structure
   - `calculate_trade_metrics()` - Trade performance metrics
   - `trades_to_dict_list()` - Conversion utilities

5. **`utils.strategy.indicators`**
   - `sma()`, `ema()` - Moving averages
   - More indicators can be added as needed

### Integration Priorities:

1. **High Priority** - Use common enums and data structures
2. **Medium Priority** - Leverage calculation functions
3. **Low Priority** - Customize where strategy-specific logic is needed

### Best Practices:

1. **Import from utils first** - Check if functionality exists in utils before implementing
2. **Contribute back** - If you create reusable functions, consider adding to utils
3. **Maintain independence** - Strategies should still be customizable
4. **Document deviations** - If you can't use utils functions, document why

## Runner Structure

### Single Runner (runner/single_runner.py)

**Requirements:**
- Execute strategy on single instrument
- Use strategy's modular components
- Generate reports using `ReportController`

### Batch Runner (runner/batch_runner.py)

**Requirements:**
- Extend `utils.runners.base_batch_runner.BatchRunner`
- Execute strategy across multiple instruments
- Use parallel processing where appropriate
- Generate consolidated reports

## Testing Requirements

Each module should include:
- Unit tests for core functions
- Integration tests for module interactions
- Mock data for testing edge cases
- Performance tests for computational functions

## Documentation Standards

- All functions must have docstrings with Args/Returns
- Include usage examples for complex functions
- Document any deviations from utils patterns
- Maintain changelog for module updates

---

*This guide ensures consistent implementation while maximizing code reuse through utils integration.* 