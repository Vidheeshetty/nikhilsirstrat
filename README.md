# NTbasedPlatform

A modular platform for backtesting and live trading strategies on NSE using Nautilus Trader.

## Structure

```
NTbasedPlatform/
├── src/
│   ├── strategies/
│   │   └── my_nse_strategy/
│   │       ├── strategy.py
│   │       ├── config.py
│   │       ├── config/
│   │       │   └── strategy.yaml
│   │       └── runners/
│   │           ├── backtest_runner.py
│   │           ├── papertrade_runner.py
│   │           └── live_runner.py
│   ├── data/
│   │   └── nse/
│   └── utils/
│       └── data_utils.py
├── catalog-data/
│   └── my_nse_strategy/
│       ├── catalog/
│       └── catalog-meta/
├── requirements.txt
└── README.md
```

## Quick Start

### 📚 Documentation
- **Getting Started**: See `UserDocumentation/index.html` for user guides
- **Development**: Check `docs/development-standards/` for framework documentation
- **Examples**: Explore `examples/` for working code samples

### 🚀 Usage
- **Data Setup**: Place raw NSE data in `data/` and use conversion tools in `scripts/data_import/`
- **Strategy Development**: Follow the framework in `docs/development-standards/`
- **Examples**: Run examples in `examples/data_usage/using_nser_catalog_data.py`
- **Backtesting**: Use strategy runners or `scripts/run_backtest.py`
- **Paper Trading**: Configure and run with `scripts/run_paper_trading.py` 