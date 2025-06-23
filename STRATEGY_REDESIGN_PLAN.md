# Modular Strategy Architecture Redesign Plan

## Overview
This document outlines a plan to refactor `strategy.py` into a modular, extensible package. The goal is to separate generic, reusable components (signals, risk, state, etc.) into a common location, making it easy to build and maintain multiple strategies with shared logic.

---

## 1. Create a Common Strategies Base

**Directory:**
```
src/strategies/common/
```

**Files:**
- `base_strategy.py`: Abstract base class for all strategies (extends Nautilus `Strategy` and provides hooks for signals, risk, state, etc).
- `signals.py`: Generic signal generators (e.g., breakout, mean reversion, etc).
- `risk.py`: Generic risk management (stop loss, take profit, trailing, breakeven, etc).
- `state.py`: Generic state tracking helpers (position, trade history, etc).
- `events.py`: Event handling utilities (wrappers, helpers for event types).
- `utils.py`: Miscellaneous helpers (e.g., price validation, rolling window, etc).

---

## 2. Refactor MyNSEStrategy to Use Common Components

**Directory:**
```
src/strategies/my_nse_strategy/strategy/
```

**Files:**
- `__init__.py`: Exposes the main strategy class.
- `my_nse_strategy.py`: Implements `MyNSEStrategy`, inheriting from `common.base_strategy.BaseStrategy`.
- `config.py`: Strategy-specific config/validation (already exists).
- `custom_signals.py`: (Optional) Any custom signals unique to this strategy.
- `custom_risk.py`: (Optional) Any custom risk logic unique to this strategy.

---

## 3. Design Principles
- **BaseStrategy**: All strategies inherit from a common abstract base, which handles event routing, state, and provides hooks for signals/risk/entry/exit.
- **Signals**: All signal logic (breakout, momentum, etc.) is in `common/signals.py` and can be composed in any strategy.
- **Risk**: All risk logic (SL, TP, trailing, etc.) is in `common/risk.py`.
- **State**: State helpers (position tracking, trade history) are in `common/state.py`.
- **Events/Utils**: Any event wrappers or helpers are in `common/events.py` and `common/utils.py`.
- **Strategy-specific files**: Only contain what is unique to that strategy.

---

## 4. Example Directory Structure
```
src/strategies/
    common/
        __init__.py
        base_strategy.py
        signals.py
        risk.py
        state.py
        events.py
        utils.py
    my_nse_strategy/
        strategy/
            __init__.py
            my_nse_strategy.py
            config.py
            custom_signals.py  # optional
            custom_risk.py    # optional
```

---

## 5. Example Usage

**my_nse_strategy.py:**
```python
from strategies.common.base_strategy import BaseStrategy
from strategies.common.signals import breakout_signal, iv_filter, oi_filter
from strategies.common.risk import dynamic_sl_tp, trailing_stop, breakeven, eod_close
from strategies.common.state import TradeState

class MyNSEStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.signal_fn = lambda tick, state: (
            breakout_signal(tick, state) and
            iv_filter(tick, state, config) and
            oi_filter(tick, state, config)
        )
        self.risk_fns = [
            lambda *a, **kw: dynamic_sl_tp(*a, **kw, config=config),
            trailing_stop,
            breakeven,
            eod_close,
        ]
        self.state = TradeState()
```

---

## 6. Mapping from Current strategy.py

### Generic (move to `common/`):
- Rolling window breakout logic → `signals.py`
- Implied volatility and open interest filters → `signals.py` or `utils.py`
- Risk management (SL, TP, trailing, breakeven, EOD close) → `risk.py`
- Position management helpers → `state.py`
- Quote tick validation → `utils.py`
- Trade tracking, order counting, active orders → `state.py`
- Event handling helpers → `events.py`
- Metadata loading (if used by multiple strategies) → `utils.py` or `state.py`

### Strategy-specific (stays in `my_nse_strategy/strategy/`):
- The class `MyNSEStrategy` itself, which:
    - Inherits from `BaseStrategy`
    - Composes generic signals/risk/state as needed
    - Implements only the unique combination/configuration of those components
    - Handles any custom overrides or unique logic

---

## 7. How to Add a New Strategy
- Create a new folder: `src/strategies/another_strategy/strategy/`
- Implement a new strategy class inheriting from `BaseStrategy`
- Compose with generic signals/risk/state as needed
- Add only custom logic if required

---

## 8. Next Steps
- Review the rest of `strategy.py` to map every function/class to its new home.
- Propose a file-by-file breakdown for both `common/` and `my_nse_strategy/strategy/`.
- (After approval) Actually refactor and move the code. 