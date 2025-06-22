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

## Usage
- Place your raw NSE data in `src/data/nse/`
- Use `data_utils.py` to convert CSV to Parquet
- Use `src/strategies/my_nse_strategy/runners/backtest_runner.py` to backtest your strategy
- Use `src/strategies/my_nse_strategy/runners/papertrade_runner.py` for paper trading
- Use `src/strategies/my_nse_strategy/runners/live_runner.py` for live trading 