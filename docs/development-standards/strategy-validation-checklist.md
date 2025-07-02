# Strategy Validation Checklist

## Pre-Submission Checklist

Before submitting a new strategy for review, ensure all items in this checklist are completed:

## ✅ Directory Structure

- [ ] **Correct directory structure** follows the [Strategy Structure Template](./strategy-structure-template.md)
- [ ] **All required files** are present:
  - [ ] `__init__.py` (root level)
  - [ ] `config.py`
  - [ ] `strategy.py`
  - [ ] `entry.py`
  - [ ] `exit.py`
  - [ ] `risk.py`
  - [ ] `position.py`
  - [ ] `runner/__init__.py`
  - [ ] `runner/backtest_runner/__init__.py`
  - [ ] `runner/backtest_runner/single_runner.py`
  - [ ] `runner/backtest_runner/batch_runner.py`
- [ ] **Placeholder files** for future development:
  - [ ] `runner/live_runner.py`
  - [ ] `runner/paper_runner.py`

## ✅ Code Quality

### Base Class Compliance
- [ ] **Strategy extends BaseStrategy** from `utils.strategy.base_strategy`
- [ ] **Implements required methods**:
  - [ ] `_setup()`
  - [ ] `on_quote(price: float)`
  - [ ] `on_stop()`
- [ ] **Uses config_class attribute** correctly

### Module Implementation
- [ ] **Entry module** follows required patterns:
  - [ ] Exports `Direction` enum
  - [ ] Exports `compute_signal` function
  - [ ] Returns proper tuple format
- [ ] **Exit module** follows required patterns:
  - [ ] Exports `ExitReason` constants
  - [ ] Exports `should_exit` function
  - [ ] Handles multiple exit criteria
- [ ] **Risk module** implements `RiskManager` class
- [ ] **Position module** implements `calculate_size` function

### Runner Implementation
- [ ] **Single runner** class name follows convention: `{StrategyName}BacktestRunner`
- [ ] **Batch runner** class name follows convention: `{StrategyName}BatchRunner`
- [ ] **Batch runner** uses `ReportController(mode="backtesting")`
- [ ] **Both runners** integrate with utils package properly

## ✅ Documentation

- [ ] **All modules** have descriptive docstrings
- [ ] **All classes** have docstrings explaining their purpose
- [ ] **All public methods** have docstrings with Args/Returns sections
- [ ] **Type hints** are present on all function signatures
- [ ] **Exports** are properly defined with `__all__` lists

## ✅ Configuration

- [ ] **Config class** uses `@dataclass(slots=True)`
- [ ] **Config class** implements `from_yaml()` classmethod
- [ ] **Config class** implements `to_dict()` method
- [ ] **Default values** are sensible and documented
- [ ] **instrument_id** parameter is included

## ✅ Integration

### Utils Package Integration
- [ ] **Uses BaseStrategy** from utils.strategy
- [ ] **Uses BatchRunner** from utils.runners
- [ ] **Uses ReportController** from utils.reporting
- [ ] **Uses calculate_metrics** from utils.runners.metrics
- [ ] **No duplicate implementations** of utils functionality

### Naming Conventions
- [ ] **Strategy name** uses PascalCase
- [ ] **File names** use snake_case
- [ ] **Class names** use PascalCase with appropriate suffixes
- [ ] **Function names** use snake_case
- [ ] **Constants** use UPPER_SNAKE_CASE

## ✅ Testing

- [ ] **Unit tests** exist for core modules
- [ ] **Integration tests** verify module interactions
- [ ] **Edge case tests** handle boundary conditions
- [ ] **Import tests** verify all modules can be imported
- [ ] **Runner tests** verify both single and batch execution

### Test Coverage
- [ ] **Entry logic** is tested with various market conditions
- [ ] **Exit logic** is tested for all exit reasons
- [ ] **Risk management** is tested with edge cases
- [ ] **Position sizing** is tested with various inputs
- [ ] **Configuration** loading and validation is tested

## ✅ Performance

- [ ] **No obvious performance bottlenecks** in signal computation
- [ ] **Vectorized operations** used where appropriate
- [ ] **Memory usage** is reasonable for expected data volumes
- [ ] **Batch processing** completes in reasonable time

## ✅ Error Handling

- [ ] **Graceful handling** of insufficient data
- [ ] **Proper exception handling** with logging
- [ ] **Input validation** for configuration parameters
- [ ] **Fallback behavior** for edge cases

## ✅ Compatibility

### Python Version
- [ ] **Compatible with Python 3.11+**
- [ ] **Uses modern type hints** (e.g., `list[str]` instead of `List[str]`)
- [ ] **No deprecated features** or warnings

### Dependencies
- [ ] **Only uses approved dependencies** from platform requirements
- [ ] **No additional external dependencies** without approval
- [ ] **Imports are properly organized** and follow conventions

## ✅ Final Validation

### Automated Checks
- [ ] **All imports work** without errors
- [ ] **Strategy can be instantiated** with default config
- [ ] **Single runner executes** without errors
- [ ] **Batch runner executes** without errors
- [ ] **Reports are generated** correctly

### Manual Review
- [ ] **Code follows platform patterns** established by reference strategies
- [ ] **Logic is sound** and implements intended strategy correctly
- [ ] **Performance is acceptable** for production use
- [ ] **Documentation is complete** and accurate

## Validation Commands

Run these commands to validate your strategy:

```bash
# Test imports
python -c "from src.strategies.{strategy_name}.strategy import {StrategyName}Strategy; print('✅ Strategy import')"
python -c "from src.strategies.{strategy_name}.runner.backtest_runner import {StrategyName}BatchRunner; print('✅ Batch runner import')"

# Run tests
pytest tests/strategies/{strategy_name}/ -v

# Run sample backtest
python scripts/run_backtest.py --strategy {strategy_name} --instrument_id NIFTY.FUT.NSE
```

## Approval Process

1. **Self-validation**: Complete this entire checklist
2. **Peer review**: Have another developer review the implementation
3. **Integration testing**: Verify strategy works with platform systems
4. **Performance testing**: Ensure acceptable performance characteristics
5. **Documentation review**: Verify all documentation is complete and accurate

---

**Note**: This checklist should be updated as the framework evolves. Any changes to requirements should be reflected here and in the related documentation.

*Framework Version: 1.0* 