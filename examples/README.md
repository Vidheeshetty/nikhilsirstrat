# Examples Directory

This directory contains **working code examples** and **sample outputs** to help users understand and use the NTbasedPlatform.

## 📁 Directory Structure

```
examples/
├── README.md                           # This file
├── data_usage/                         # Data integration examples
│   ├── using_nser_catalog_data.py     # NSER futures data example
│   ├── csv_to_parquet_example.py      # Data conversion example (planned)
│   └── data_validation_example.py     # Data quality checks (planned)
├── strategy_development/               # Strategy development examples
│   ├── minimal_strategy_example.py    # Basic strategy template (planned)
│   ├── utils_integration_example.py   # Utils usage examples (planned)
│   └── testing_strategy_example.py    # Strategy testing patterns (planned)
├── configuration/                      # Configuration examples
│   ├── backtest_config_example.yaml   # Backtest configuration (planned)
│   ├── batch_run_example.yaml         # Batch execution config (planned)
│   └── paper_trading_config_example.yaml # Paper trading setup (planned)
├── sample_outputs/                     # Example outputs and reports
│   ├── backtesting/                    # Sample backtest reports
│   └── papertrading/                   # Sample paper trading reports
│       └── individual/
│           └── 2025-06-29/
│               └── 15-46-17_trend_riding/
└── jupyter_notebooks/                  # Interactive examples (planned)
    ├── getting_started.ipynb          # Platform introduction
    ├── strategy_analysis.ipynb        # Strategy performance analysis
    └── parameter_optimization.ipynb   # Parameter sweep examples
```

## 🎯 Purpose & Audience

### **Working Code Examples**
- **Executable scripts** that demonstrate platform features
- **Copy-paste ready** code for common tasks
- **Learning by doing** approach for new users

### **Sample Outputs**
- **Reference reports** showing expected output formats
- **Template structures** for custom reporting
- **Quality benchmarks** for validation

### **Target Audiences**
1. **New Users** - Getting started with the platform
2. **Strategy Developers** - Learning framework patterns
3. **Data Engineers** - Understanding data integration
4. **DevOps/Admins** - Configuration and deployment examples

## 📚 How Examples Relate to Documentation

### **Examples** vs **Documentation**:
- **Examples**: "Here's working code that does X"
- **Documentation**: "Here's how X works and why"

### **Cross-References**:
- Examples reference relevant documentation sections
- Documentation points to working examples
- Both maintained in sync for consistency

## 🚀 Current Examples

### 1. **Data Usage Examples**

#### `using_nser_catalog_data.py`
**Purpose**: Demonstrates how to load and analyze NSER NIFTY futures data

**What it shows**:
- Loading data from Nautilus Trader catalog
- Accessing instrument information
- Extracting price data for strategy use
- Basic statistical analysis

**Usage**:
```bash
cd examples
python using_nser_catalog_data.py
```

**Related Documentation**:
- [Data Conversion Tools](../guide/user/data_conversion_tools.html)
- [Strategy Development Framework](../docs/development-standards/strategy-development-framework.md)

### 2. **Sample Outputs**

#### Paper Trading Reports
**Location**: `sample_outputs/papertrading/individual/2025-06-29/15-46-17_trend_riding/`

**Purpose**: Shows expected paper trading output structure
- Report formatting and styling
- Asset organization (CSS, images)
- File naming conventions

## 🔧 Planned Enhancements

### **Short Term** (Next Sprint)
1. **Strategy Development Examples**
   - Minimal strategy template
   - Utils integration patterns
   - Testing examples

2. **Configuration Examples**
   - Backtest configuration templates
   - Batch execution examples
   - Parameter sweep configurations

### **Medium Term** (Next Month)
1. **Jupyter Notebooks**
   - Interactive getting started guide
   - Strategy analysis workflows
   - Parameter optimization tutorials

2. **Advanced Examples**
   - Multi-strategy portfolio examples
   - Custom indicator development
   - Performance optimization patterns

### **Long Term** (Future)
1. **Integration Examples**
   - Broker integration patterns
   - Live trading examples
   - Monitoring and alerting setup

## 🎓 Learning Path

### **For New Users**:
1. Start with `using_nser_catalog_data.py`
2. Review sample outputs in `sample_outputs/`
3. Follow strategy development examples (planned)
4. Explore configuration examples (planned)

### **For Strategy Developers**:
1. Study framework documentation in `docs/development-standards/`
2. Run strategy development examples
3. Examine utils integration examples
4. Use testing patterns from examples

### **For Advanced Users**:
1. Explore advanced configuration examples
2. Study performance optimization patterns
3. Review integration examples
4. Contribute new examples back to the repository

## 🤝 Contributing Examples

### **Guidelines**:
1. **Executable**: All examples must run without modification
2. **Documented**: Include clear comments and docstrings
3. **Self-contained**: Minimize external dependencies
4. **Cross-referenced**: Link to relevant documentation

### **Process**:
1. Create example in appropriate subdirectory
2. Test thoroughly on clean environment
3. Add entry to this README
4. Update related documentation with cross-references

## 📞 Support

- **For example usage questions**: Check comments in example files
- **For platform questions**: See documentation in `docs/` and `guide/`
- **For user guides**: Check `guide/user/`
- **For development standards**: See `docs/development-standards/`

---

*Examples are living code that evolves with the platform. Keep them current and useful!* 