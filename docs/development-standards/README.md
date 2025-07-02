# Development Standards Documentation

This directory contains the standardized framework and guidelines for developing trading strategies in the NTbasedPlatform.

## 📋 Quick Start

For new strategy development, follow this sequence:

1. **Read the Framework** → [Strategy Development Framework](./strategy-development-framework.md)
2. **Use the Template** → [Strategy Structure Template](./strategy-structure-template.md)
3. **Implement Modules** → [Module Implementation Guide](./module-implementation-guide.md)
4. **Integrate Utils** → [Utils Integration Guide](./utils-integration-guide.md)
5. **Validate Your Work** → [Strategy Validation Checklist](./strategy-validation-checklist.md)

## 📚 Documentation Index

### Core Framework
- **[Strategy Development Framework](./strategy-development-framework.md)** - Main framework overview and principles
- **[Strategy Structure Template](./strategy-structure-template.md)** - Required directory structure and file templates
- **[Module Implementation Guide](./module-implementation-guide.md)** - Detailed implementation requirements for each module
- **[Utils Integration Guide](./utils-integration-guide.md)** - Comprehensive guide for leveraging utils package

### Quality Assurance
- **[Strategy Validation Checklist](./strategy-validation-checklist.md)** - Comprehensive checklist before code submission
- **[Testing Requirements](./testing-requirements.md)** - Testing standards and patterns *(Coming Soon)*
- **[Runner Development Guide](./runner-development-guide.md)** - Runner-specific implementation details *(Coming Soon)*

### Development Workflow
- **[Git Sync Troubleshooting](./git_sync_troubleshooting.md)** - Guide for resolving Git synchronization issues between developers
- **[Paper Trading Folder Structure](./paper_trading_folder_structure.md)** - Documentation for the new date-wise paper trading log organization

### Optimizations & Efficiency
- **[Optimization Suggestions](./optimization_suggestions.md)** - Backtesting framework optimization ideas
- **[Efficiency Improvements](./EFFICIENCY_IMPROVEMENTS.md)** - Data catalog efficiency improvements

## 🎯 Framework Goals

1. **Consistency** - All strategies follow the same patterns and structure
2. **Maintainability** - Modular design makes code easy to understand and modify
3. **Reusability** - Maximum leverage of platform utilities and common functionality
4. **Quality** - Standardized validation ensures high code quality
5. **Scalability** - Framework supports both simple and complex strategy implementations

## 🔧 Utils Integration

The framework emphasizes maximum code reuse through the `utils.strategy` package:

### Available Utils Modules:
- **`utils.strategy.enums`** - Common enums (Direction, ExitReason, OrderSide)
- **`utils.strategy.position`** - Position sizing functions
- **`utils.strategy.risk`** - Risk management calculations
- **`utils.strategy.trades`** - Trade record structures and utilities
- **`utils.strategy.indicators`** - Technical analysis functions

### Integration Benefits:
- **Consistency** - Standardized enums and data structures across all strategies
- **Reliability** - Well-tested, optimized functions reduce bugs
- **Maintainability** - Centralized updates benefit all strategies simultaneously
- **Performance** - Optimized implementations for common operations

## 🏗️ Architecture Overview

```
Strategy Framework
├── BaseStrategy (from utils.strategy)
├── Modular Components
│   ├── entry.py (signal generation)
│   ├── exit.py (exit conditions)
│   ├── risk.py (risk management)
│   └── position.py (position sizing)
├── Configuration System
│   └── dataclass-based config with YAML support
└── Runner System
    ├── Single Runner (individual instruments)
    └── Batch Runner (parallel execution)
```

## 📝 Reference Implementations

Two strategies serve as reference implementations of this framework:

- **Trend Riding Strategy** (`src/strategies/trend_riding/`)
  - Breakout-based trend following
  - Full modular implementation
  - Complete runner suite

- **Swing Range Expansion Strategy** (`src/strategies/swing_range_expansion/`)
  - NR7 pattern detection with breakout trading
  - Recently refactored to match framework
  - Demonstrates framework compliance

## 🔄 Framework Evolution

This framework is designed to evolve with the platform. When making changes:

1. **Update Documentation** - Modify relevant guides and templates
2. **Update Reference Strategies** - Ensure examples remain current
3. **Update Validation Tools** - Keep checklist and validation commands current
4. **Communicate Changes** - Document breaking changes and migration paths

## 🚀 Getting Started

To create a new strategy:

```bash
# 1. Choose your strategy name (PascalCase)
STRATEGY_NAME="MyNewStrategy"

# 2. Create directory structure
mkdir -p src/strategies/my_new_strategy/runner/backtest_runner

# 3. Follow the templates in strategy-structure-template.md
# 4. Implement required modules per module-implementation-guide.md
# 5. Validate using strategy-validation-checklist.md
```

## 📞 Support

- **Framework Questions** - Refer to the detailed guides in this directory
- **Implementation Help** - Study the reference strategies
- **Validation Issues** - Use the validation checklist and commands

## 🤖 AI Pair-Programming Integration

The framework is enforced through AI pair-programming rules in `docs/cursor_rules.md`:
- Prevents framework violations during development
- Guides developers to use utils integration opportunities
- Ensures consistent architecture across strategies
- Validates compliance before code submission

---

*Last Updated: 2025-06-29*  
*Framework Version: 1.1* 