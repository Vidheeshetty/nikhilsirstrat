# Strategy Structure Template

## Directory Structure

Every strategy must follow this exact directory structure:

```
src/strategies/{strategy_name}/
├── __init__.py                     # Package initialization
├── config.py                      # Configuration schema
├── strategy.py                    # Main strategy class
├── entry.py                       # Entry signal logic
├── exit.py                        # Exit signal logic  
├── risk.py                        # Risk management
├── position.py                    # Position sizing
├── runner/                        # Execution runners
│   ├── __init__.py
│   ├── backtest_runner/
│   │   ├── __init__.py
│   │   ├── single_runner.py      # Single instrument execution
│   │   ├── batch_runner.py       # Multi-instrument execution
│   │   ├── config.py             # Runner-specific config
│   │   ├── engine.py             # Engine utilities
│   │   └── metrics.py            # Strategy-specific metrics
│   ├── live_runner.py            # Live trading (placeholder)
│   └── paper_runner.py           # Paper trading (placeholder)
└── {strategy_name}.yaml           # Default configuration file
```

## File Templates

### 1. `__init__.py` (Root)
```python
"""Strategy package for {StrategyName}."""

from .strategy import {StrategyName}Strategy  # noqa: F401
from .config import {StrategyName}Config  # noqa: F401

__all__ = ["{StrategyName}Strategy", "{StrategyName}Config"]
```

### 2. `config.py`
```python
from __future__ import annotations

import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

"""Configuration schema for {StrategyName} strategy."""

@dataclass(slots=True)
class {StrategyName}Config:
    """Configuration parameters for {StrategyName} strategy."""
    
    # Core parameters
    instrument_id: str = "NIFTY.FUT.NSE"
    
    # Strategy-specific parameters
    # Add your parameters here
    
    @classmethod
    def from_yaml(
        cls, path: str | Path, *, instrument_id: str | None = None, **overrides
    ) -> {StrategyName}Config:
        """Load configuration from YAML file with optional overrides."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        if instrument_id:
            data["instrument_id"] = instrument_id
        data.update(overrides)
        
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

__all__ = ["{StrategyName}Config"]
```

### 3. `strategy.py`
```python
from __future__ import annotations

from typing import List, Optional
from utils.strategy.base_strategy import BaseStrategy
from .config import {StrategyName}Config
from .entry import compute_signal, Direction
from .exit import should_exit
from .risk import RiskManager
from .position import calculate_size

"""{StrategyName} Strategy implementation."""

class {StrategyName}Strategy(BaseStrategy):
    """Main strategy class for {StrategyName}."""

    config_class = {StrategyName}Config

    def _setup(self) -> None:
        """Initialize strategy state."""
        # Initialize your strategy state here
        super()._setup()

    def on_quote(self, price: float):
        """Process new quote/price data."""
        # Implement your trading logic here
        pass

    def on_stop(self):
        """Strategy cleanup."""
        super().on_stop()
        # Add cleanup logic here

__all__ = ["{StrategyName}Strategy"]
```

## Naming Conventions

1. **Strategy Name**: Use PascalCase (e.g., `TrendRiding`, `SwingRangeExpansion`)
2. **File Names**: Use snake_case (e.g., `entry.py`, `risk.py`)
3. **Class Names**: Use PascalCase with Strategy suffix (e.g., `TrendRidingStrategy`)
4. **Function Names**: Use snake_case (e.g., `compute_signal`, `calculate_size`)
5. **Constants**: Use UPPER_SNAKE_CASE (e.g., `DEFAULT_LOOKBACK`)

## Required Exports

Each module must export its public interface via `__all__`:

```python
__all__ = ["ClassName", "function_name", "CONSTANT_NAME"]
```

## Documentation Requirements

1. **Module Docstrings**: Every module must have a descriptive docstring
2. **Class Docstrings**: Every class must document its purpose
3. **Method Docstrings**: Public methods must have docstrings with Args/Returns
4. **Type Hints**: All functions must have proper type annotations

## Integration Points

### BaseStrategy Methods
Your strategy must implement:
- `_setup()` - Initialize strategy state
- `on_quote(price: float)` - Process price updates
- `on_stop()` - Cleanup when strategy stops

### Utils Integration
Use these platform utilities:
- `utils.strategy.base_strategy.BaseStrategy` - Base class
- `utils.runners.base_batch_runner.BatchRunner` - Batch execution
- `utils.reporting.controller.ReportController` - Report generation
- `utils.runners.metrics.calculate_metrics` - Performance metrics

---

*See [Module Implementation Guide](./module-implementation-guide.md) for detailed module requirements.* 