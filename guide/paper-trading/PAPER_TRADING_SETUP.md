# Paper Trading Setup Guide

## Overview

This document provides a comprehensive guide for setting up and running paper trading with multiple brokers, starting with Zerodha integration. The system provides realistic simulation of live trading with proper risk management, reporting, and monitoring.

## Architecture

### Core Components

1. **Broker Integration Layer** (`src/brokers/`)
   - Abstract base broker interface
   - Zerodha-specific implementation
   - Paper trading simulator
   - Multi-broker manager

2. **Paper Trading Engine** (`scripts/run_paper_trading.py`)
   - Main orchestration engine
   - Strategy coordination
   - Risk management
   - Real-time monitoring

3. **Reporting System** (`utils/reporting/`)
   - Real-time dashboard
   - End-of-day reports
   - Performance analytics
   - Multi-format output

4. **Configuration Management** (`config/paper_trading.yaml`)
   - Broker settings
   - Strategy configuration
   - Risk parameters
   - Reporting options

## Directory Structure

```
├── src/brokers/                    # Broker integration
│   ├── base.py                     # Abstract broker interface
│   ├── manager.py                  # Multi-broker manager
│   ├── paper.py                    # Paper trading simulator
│   └── zerodha/                    # Zerodha integration
│       ├── broker.py               # Zerodha broker implementation
│       ├── config.py               # Zerodha configuration
│       └── client.py               # KiteConnect client wrapper
├── config/paper_trading.yaml       # Main configuration
├── scripts/run_paper_trading.py    # Main runner script
├── utils/reporting/                # Reporting system
└── runlogs/papertrading/           # Output logs and reports
```

## Setup Instructions

### 1. Configuration

Edit `config/paper_trading.yaml` to configure your paper trading setup:

```yaml
# Broker Configuration
brokers:
  zerodha:
    broker_name: "zerodha"
    paper_trading: true
    paper_initial_balance: 1000000.0  # 10 Lakh starting balance
    
    # Risk management
    max_position_size: 100
    max_daily_loss: 50000.0
    max_open_positions: 10

# Strategy Configuration
strategies:
  trend_riding:
    enabled: true
    broker: "zerodha"
    config_file: "src/strategies/trend_riding/config.yaml"
  
  swing_range_expansion:
    enabled: true
    broker: "zerodha"
    config_file: "src/strategies/swing_range_expansion/config.yaml"
```

### 2. Running Paper Trading

#### Basic Usage

```bash
# Run all configured strategies
python scripts/run_paper_trading.py

# Run specific strategy only
python scripts/run_paper_trading.py --strategy trend_riding

# Use custom configuration
python scripts/run_paper_trading.py --config config/my_paper_config.yaml

# Verbose logging
python scripts/run_paper_trading.py --verbose
```

#### Command Line Options

- `--config`: Configuration file path (default: `config/paper_trading.yaml`)
- `--strategy`: Run specific strategy only
- `--dry-run`: Dry run mode (no actual orders)
- `--verbose`: Enable verbose logging

### 3. Monitoring and Reports

#### Real-time Monitoring

The system provides real-time monitoring through:

1. **Live Dashboard**: `runlogs/papertrading/{session_id}/live_dashboard.html`
2. **Console Logs**: Real-time strategy and order updates
3. **Live Data Files**: JSON and CSV files updated in real-time

#### End-of-Day Reports

Generated automatically at session end:

1. **HTML Report**: Comprehensive visual report with charts
2. **JSON Report**: Machine-readable session data
3. **CSV Files**: Trade history and performance metrics

#### Report Locations

```
runlogs/papertrading/{session_id}/
├── live_dashboard.html           # Real-time dashboard
├── paper_trading_report.html     # End-of-day HTML report
├── paper_trading_report.json     # Session data export
├── trades.csv                    # Trade history
├── performance.csv               # Performance metrics
├── live_data.json               # Latest snapshot
└── session_metadata.json        # Session information
```

## Broker Integration

### Current Support

#### Zerodha (Paper Trading)
- ✅ Paper trading simulation
- ✅ Realistic order execution
- ✅ Commission and slippage modeling
- ✅ Position tracking
- ⏳ Live KiteConnect integration (planned)

#### Future Brokers
- 📋 Upstox
- 📋 Angel One
- 📋 ICICI Direct
- 📋 5paisa

### Adding New Brokers

1. Create broker package: `src/brokers/{broker_name}/`
2. Implement broker class extending `BaseBroker`
3. Create broker-specific configuration class
4. Register in `BrokerManager`
5. Update configuration files

Example structure:
```python
# src/brokers/new_broker/broker.py
class NewBroker(BaseBroker):
    async def place_order(self, order: Order) -> str:
        # Implement broker-specific order placement
        pass
```

## Risk Management

### Built-in Risk Controls

1. **Position Limits**
   - Maximum position size per instrument
   - Maximum number of open positions
   - Position concentration limits

2. **Loss Limits**
   - Daily loss limits per broker
   - Maximum drawdown limits
   - Emergency stop triggers

3. **Order Controls**
   - Order size validation
   - Price reasonableness checks
   - Duplicate order prevention

### Configuration

```yaml
risk_management:
  global_max_daily_loss: 100000.0    # Max daily loss across all strategies
  global_max_positions: 20           # Max positions across all strategies
  position_size_limit: 0.05          # Max 5% of account per position
  
  # Emergency stops
  emergency_stop_loss: 0.10           # 10% emergency stop
  max_drawdown_limit: 0.15            # 15% max drawdown
```

## Strategy Integration

### Supported Strategies

1. **Trend Riding Strategy**
   - Breakout-based entries
   - Dynamic stop-loss management
   - Configurable risk parameters

2. **Swing Range Expansion Strategy**
   - NR7 pattern detection
   - R-multiple based exits
   - Volatility-based position sizing

### Adding Custom Strategies

1. Create strategy runner extending base runner
2. Implement broker integration methods
3. Add configuration to `paper_trading.yaml`
4. Register in engine initialization

## Performance Analytics

### Key Metrics Tracked

1. **P&L Metrics**
   - Total P&L (realized + unrealized)
   - Daily P&L
   - Maximum drawdown
   - Sharpe ratio

2. **Trade Metrics**
   - Win rate
   - Average win/loss
   - Risk-reward ratio
   - Trade frequency

3. **Position Metrics**
   - Open positions count
   - Position duration
   - Position sizing

4. **Risk Metrics**
   - VaR (Value at Risk)
   - Maximum consecutive losses
   - Drawdown duration

### Custom Analytics

Extend `utils/reporting/analytics.py` to add custom metrics:

```python
def calculate_custom_metric(trades: List[Dict]) -> float:
    # Implement custom calculation
    return result
```

## Market Simulation

### Paper Trading Features

1. **Realistic Execution**
   - Order delays (100-500ms)
   - Slippage simulation (0-2%)
   - Fill probability (98%)

2. **Market Data Simulation**
   - Price movement modeling
   - Volume simulation
   - Bid-ask spread simulation

3. **Commission Structure**
   - Zerodha-like brokerage (₹20 per order)
   - STT (0.025% on sell side)
   - Transaction charges (0.00325%)
   - GST (18% on brokerage)

### Configuration

```yaml
# Market simulation settings
execution_delay_min: 0.1      # seconds
execution_delay_max: 0.5
slippage_min: 0.0            # percentage
slippage_max: 0.02
fill_probability: 0.98
```

## Logging and Debugging

### Log Levels

- `DEBUG`: Detailed execution information
- `INFO`: General operational messages
- `WARNING`: Risk events and warnings
- `ERROR`: Error conditions
- `CRITICAL`: Emergency stops and critical failures

### Log Files

```
runlogs/papertrading/
├── paper_trading.log          # Main application log
├── {session_id}/
│   ├── broker.log            # Broker-specific logs
│   ├── strategy.log          # Strategy execution logs
│   └── risk.log              # Risk management logs
```

### Debug Mode

Enable detailed debugging:

```yaml
development:
  debug_orders: true
  debug_positions: true
  debug_trades: true
```

## Troubleshooting

### Common Issues

1. **Broker Connection Failures**
   - Check configuration file syntax
   - Verify broker credentials (for live trading)
   - Check network connectivity

2. **Strategy Loading Errors**
   - Verify strategy configuration files exist
   - Check strategy import paths
   - Validate strategy parameters

3. **Performance Issues**
   - Reduce update frequency for large position counts
   - Disable real-time dashboard for high-frequency strategies
   - Use CSV format instead of JSON for large datasets

### Error Recovery

The system includes automatic error recovery:

1. **Broker Failover**: Automatic switching to backup brokers
2. **Strategy Restart**: Automatic strategy restart on errors
3. **Data Recovery**: Session data persistence for crash recovery

## Best Practices

### Configuration Management

1. **Environment-Specific Configs**: Use separate configs for development/testing/production
2. **Parameter Validation**: Always validate configuration parameters
3. **Backup Configs**: Keep backup copies of working configurations

### Risk Management

1. **Start Small**: Begin with small position sizes and low risk limits
2. **Monitor Closely**: Watch initial sessions closely for unexpected behavior
3. **Gradual Scaling**: Increase position sizes gradually as confidence builds

### Performance Optimization

1. **Batch Operations**: Use batch operations for multiple orders/queries
2. **Efficient Logging**: Use appropriate log levels to avoid performance impact
3. **Resource Monitoring**: Monitor CPU and memory usage during long sessions

## Live Trading Migration

### Preparation Steps

1. **Thorough Testing**: Run extensive paper trading sessions
2. **Risk Validation**: Validate all risk controls work correctly
3. **Performance Analysis**: Analyze strategy performance over multiple market conditions

### Configuration Changes

To migrate from paper to live trading:

```yaml
brokers:
  zerodha:
    paper_trading: false        # Enable live trading
    api_key: "your_api_key"     # Real API credentials
    api_secret: "your_secret"
    access_token: "your_token"
```

### Additional Considerations

1. **Regulatory Compliance**: Ensure compliance with local trading regulations
2. **Capital Requirements**: Ensure sufficient capital for live trading
3. **Monitoring**: Implement additional monitoring for live trading
4. **Emergency Procedures**: Have emergency stop procedures in place

## Support and Development

### Getting Help

1. **Documentation**: Check this guide and inline code documentation
2. **Logs**: Review log files for error details
3. **Configuration**: Verify configuration file syntax and parameters

### Contributing

1. **Broker Integrations**: Add support for new brokers
2. **Strategy Implementations**: Contribute new trading strategies
3. **Analytics**: Add new performance metrics and reports
4. **Testing**: Improve test coverage and add integration tests

### Future Enhancements

1. **Real-time Alerts**: Email/SMS/webhook notifications
2. **Advanced Analytics**: Machine learning-based performance analysis
3. **Portfolio Management**: Multi-strategy portfolio optimization
4. **Cloud Deployment**: Cloud-based paper trading infrastructure 