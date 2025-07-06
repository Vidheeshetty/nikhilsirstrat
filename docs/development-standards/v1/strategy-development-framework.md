# Strategy Development Framework

## Overview

This document defines the standardized framework for developing trading strategies in the NTbasedPlatform. All new strategies must conform to this structure to ensure consistency, maintainability, and proper integration with the platform's utilities.

**Important**: This framework applies to both **new strategy development** and **modifications to existing strategies**. When modifying existing strategies, they should be brought into compliance with current framework standards.

## Core Principles

1. **Modular Design** - Separate concerns into distinct modules
2. **BaseStrategy Inheritance** - Leverage common functionality
3. **Utils Integration** - Maximize reuse of platform utilities
4. **Consistent Structure** - Follow established directory patterns
5. **Proper Testing** - Include comprehensive test coverage

## Framework Components

### 1. Strategy Architecture
- **Base Class**: All strategies must extend `utils.strategy.base_strategy.BaseStrategy`
- **Modular Components**: Split logic into separate, focused modules
- **Configuration**: Use dataclass-based configuration with YAML support

### 2. Required Modules
Each strategy must implement the following modules:

- **`strategy.py`** - Main strategy class extending BaseStrategy
- **`config.py`** - Configuration schema and validation
- **`entry.py`** - Entry signal computation logic
- **`exit.py`** - Exit signal computation logic
- **`risk.py`** - Risk management functionality
- **`position.py`** - Position sizing calculations

### 3. Runner Structure
Each strategy must provide both single and batch execution capabilities:

- **Single Runner** - Execute strategy on individual instruments
- **Batch Runner** - Execute strategy across multiple instruments in parallel
- **Proper Integration** - Use platform's reporting and metrics systems

## Strategy Modification Guidelines

### When Modifying Existing Strategies:
1. **Assess Current Compliance** - Check against the [Strategy Validation Checklist](./strategy-validation-checklist.md)
2. **Plan Refactoring** - Identify areas that need to be brought into framework compliance
3. **Incremental Updates** - Make changes in stages to maintain functionality
4. **Test Thoroughly** - Ensure modifications don't break existing functionality
5. **Update Documentation** - Reflect changes in strategy documentation

### Refactoring Priorities:
1. **High Priority** - Framework violations that affect maintainability or integration
2. **Medium Priority** - Code that could benefit from utils integration
3. **Low Priority** - Style and naming convention updates

### Utils Integration Opportunities:
When modifying strategies, look for opportunities to:
- Move common signal computation logic to `utils.strategy.indicators`
- Utilize shared risk management patterns from `utils.strategy.risk`
- Leverage common position sizing algorithms from `utils.strategy.position`
- Use shared trade record structures from `utils.strategy.trades`

## Implementation Guidelines

For detailed implementation guidelines, see:
- [Strategy Structure Template](./strategy-structure-template.md)
- [Module Implementation Guide](./module-implementation-guide.md)
- [Runner Development Guide](./runner-development-guide.md)
- [Testing Requirements](./testing-requirements.md)

## Validation Checklist

Before submitting a new strategy or strategy modifications, ensure it passes the [Strategy Validation Checklist](./strategy-validation-checklist.md).

## Examples

Reference implementations:
- **Trend Riding Strategy** - `src/strategies/trend_riding/`
- **Swing Range Expansion Strategy** - `src/strategies/swing_range_expansion/`

Both strategies follow this framework and can serve as templates for new development.

## Framework Evolution

This framework is living documentation. Updates should be made through:
1. **Discussion and approval** of changes
2. **Update of this document** and related guides
3. **Refactoring of existing strategies** to match new standards
4. **Update of validation tools** and tests
5. **Communication of changes** to all developers

### Framework Update Process:
1. **Identify Need** - Framework gaps or improvement opportunities
2. **Propose Changes** - Document proposed updates with rationale
3. **Review and Approve** - Team review of proposed changes
4. **Update Documentation** - Modify framework documents
5. **Update Reference Strategies** - Ensure examples remain current
6. **Migrate Existing Code** - Update existing strategies incrementally
7. **Update Validation Tools** - Keep checklist and tools current

---

*Last Updated: 2025-06-29*  
*Framework Version: 1.1* 