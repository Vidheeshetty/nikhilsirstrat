# Batchtest Runner Rationalization & Simplification Strategy

## 1. Current Situation

Your current package for backtesting (`src/strategies/my_nse_strategy/runners/backtest/`) contains:
- `backtest_orchestrator.py`
- `batch_helpers.py`
- `config_manager.py`
- `data_manager.py`
- `engine_manager.py`
- `modular_backtest_runner.py`
- `results_processor.py`

These files likely mix:
- **Generic backtest orchestration logic** (e.g., batch running, config loading, result aggregation)
- **Strategy-specific logic** (e.g., how to instantiate a particular strategy, custom data handling, custom result metrics)

---

## 2. Goals for Refactoring

- **Separation of Concerns:**  
  Cleanly separate generic backtest logic from strategy-specific logic.
- **Reusability:**  
  Make it easy to write new backtest runners for other strategies by reusing generic components.
- **Clarity:**  
  Make it obvious which code is generic and which is strategy-specific.

---

## 3. Proposed Structure

### A. Generic Backtest Utilities (Reusable for All Strategies)
Move these to a shared package, e.g., `src/backtest_utils/` or `src/engine/backtest/`:
- **Batch Orchestration:**
  - Running multiple configs/instruments in parallel or sequence.
- **Config Management:**
  - Loading, validating, and merging YAML/JSON configs.
- **Data Management:**
  - Loading historical data, catalog access, instrument lookup.
- **Engine Management:**
  - Instantiating and running the backtest engine, handling results.
- **Results Processing:**
  - Aggregating, saving, and reporting results in a generic way.

### B. Strategy-Specific Logic
Keep these in each strategy's own directory, e.g., `src/strategies/my_nse_strategy/`:
- **Strategy Class & Config:**
  - The actual trading logic and its configuration schema.
- **Custom Data Handling:**
  - Any special data pre-processing or feature engineering unique to the strategy.
- **Custom Metrics/Reports:**
  - Any result processing that is unique to the strategy.

### C. Thin Strategy-Specific Runner
Each strategy gets a minimal runner script that:
- Imports the generic utilities.
- Instantiates the strategy and config.
- Passes them to the generic batch runner.

---

## 4. File/Module Breakdown Example

**Generic (shared):**
```
src/backtest_utils/
    batch_runner.py
    config_loader.py
    data_loader.py
    engine_launcher.py
    results_aggregator.py
```

**Strategy-specific:**
```
src/strategies/my_nse_strategy/
    strategy.py
    config.py
    custom_metrics.py
    run_backtest.py  # (very thin, just wires up the generic runner)
```

---

## 5. What is Strategy-Specific?
- The actual `Strategy` class and its config.
- Any custom data features or pre-processing.
- Any custom result metrics or reports.
- Any custom hooks (e.g., callbacks for special events).

**Everything else should be generic and reusable.**

---

## 6. Benefits
- **Rapid onboarding for new strategies:**  
  Just implement the strategy and config, and reuse the rest.
- **Less duplication:**  
  No need to copy-paste batch logic for every new strategy.
- **Easier maintenance:**  
  Bug fixes and improvements to the batch runner benefit all strategies.

---

## 7. Next Steps
- Audit each file in your current backtest runner package to classify code as generic or strategy-specific.
- Move generic code to a shared location.
- Refactor strategy runners to use the shared utilities.

---

**This document serves as a reference for future rationalization and simplification of the batchtest runner package.** 