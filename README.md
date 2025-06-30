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
- **Getting Started**: See `guide/user/index.html` for user guides
- **Development**: Check `docs/development-standards/` for framework documentation
