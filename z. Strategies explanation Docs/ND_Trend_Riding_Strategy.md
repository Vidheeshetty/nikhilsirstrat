
# ND's Trend Riding Strategy

## Overview
This trading strategy is based on **Dow Theory**, utilizing key price levels—previous tops and bottoms—to determine entries and exits. It integrates dynamic stop-loss mechanisms and strong risk management.

---

## Dow Theory Principles: Understanding Tops and Bottoms

**Key Concepts:**

- **Primary Trend:** Long-term direction (months–years).
- **Secondary Trend:** Corrections within a primary trend (weeks–months).
- **Tertiary Trend:** Minor short-term movements (days–weeks).

### Top and Bottom Definitions:
- **Top:** Highest price before a pullback.
- **Bottom:** Lowest price before an uptrend reversal.

---

## Higher Highs and Lower Lows

**Uptrend:**
- *Higher High*: Current peak > previous peak
- *Higher Low*: Current trough > previous trough

**Downtrend:**
- *Lower High*: Current peak < previous peak
- *Lower Low*: Current trough < previous trough

---

## Strategy Steps

### Step 1: Identifying Key Levels
- **Previous Top**: Breakout above signals long entry
- **Previous Bottom**: Breakdown below signals short entry

**Entry Conditions:**
- Long: Price crosses >0.1% above top (0.2% for stocks)
- Short: Price crosses <0.1% below bottom (0.2% for stocks)

### Step 2: Entry and Stop-Loss
- Long SL: Previous Bottom
- Short SL: Previous Top

### Step 3: Trailing Stop-Loss
- Adjust dynamically using HH/HL or LH/LL logic.

### Step 4: Stop and Reverse (SAR)
- Reverse with double quantity to cover prior position + new trade.

### Step 5: Risk Management
- Max Loss: 2% (indices), 3% (stocks)
- First Day Loss Cap: 1% (indices), 1.5% (stocks)
- Break-even shift after 2% favorable move.
- On gap days, use first 15-min candle for SAR reset.

### Step 6: Contract Rollover
- On expiry, close and reopen next contract at 1:30 PM IST.

---

## Pine Script: Previous High/Low Breakout

```pinescript
strategy("Previous High/Low Breakout", overlay=true)
length = input(20, title="Lookback Period")
sl_pct = input(1, title="Stop-Loss %") / 100
tp_pct = input(2, title="Take-Profit %") / 100
prevHigh = ta.highest(high, length)
prevLow = ta.lowest(low, length)

longCondition = ta.crossover(close, prevHigh)
shortCondition = ta.crossunder(close, prevLow)

longSL = close * (1 - sl_pct)
longTP = close * (1 + tp_pct)
shortSL = close * (1 + sl_pct)
shortTP = close * (1 - tp_pct)

if longCondition
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", from_entry="Long", stop=longSL, limit=longTP)

if shortCondition
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", from_entry="Short", stop=shortSL, limit=shortTP)

plot(prevHigh, title="Previous High", color=color.green, linewidth=2)
plot(prevLow, title="Previous Low", color=color.red, linewidth=2)
```

---

## Python Backtesting with Backtrader

```python
import backtrader as bt
import pandas as pd

class BreakoutStrategy(bt.Strategy):
    params = (("lookback", 20), ("sl_pct", 1), ("tp_pct", 2))
    def __init__(self):
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.lookback)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.lookback)
    def next(self):
        if not self.position:
            if self.data.close[0] > self.highest[-1]:
                sl = self.data.close[0] * (1 - self.params.sl_pct / 100)
                tp = self.data.close[0] * (1 + self.params.tp_pct / 100)
                self.buy(size=1)
                self.sell(exectype=bt.Order.Stop, price=sl, size=1)
                self.sell(exectype=bt.Order.Limit, price=tp, size=1)
            elif self.data.close[0] < self.lowest[-1]:
                sl = self.data.close[0] * (1 + self.params.sl_pct / 100)
                tp = self.data.close[0] * (1 - self.params.tp_pct / 100)
                self.sell(size=1)
                self.buy(exectype=bt.Order.Stop, price=sl, size=1)
                self.buy(exectype=bt.Order.Limit, price=tp, size=1)

df = pd.read_csv("your_data.csv", index_col="Date", parse_dates=True)
df = df[["Open", "High", "Low", "Close", "Volume"]]
data = bt.feeds.PandasData(dataname=df)
cerebro = bt.Cerebro()
cerebro.addstrategy(BreakoutStrategy)
cerebro.adddata(data)
cerebro.broker.set_cash(10000)
cerebro.broker.setcommission(commission=0.001)
cerebro.run()
cerebro.plot()
```

---

## Manual Backtesting Steps

1. Download historical OHLC data.
2. Identify tops/bottoms (20 candles lookback).
3. Mark trades per rules.
4. Log entries/exits in Excel.
5. Evaluate metrics: Win Rate, Drawdown, RR ratio, Net Profit.

---

## Automated Tools

| Tool        | Language | Notable Features |
|-------------|----------|------------------|
| TradingView | Pine     | Real-time strategy testing |
| MT4/MT5     | MQL4/5   | Forex/stocks/indices |
| Backtrader  | Python   | Custom, powerful |
| QuantConnect | C#/Python | Institutional-grade |
| Amibroker   | AFL      | Widely used, fast |

---

## Key Metrics for Evaluation

- **Net Profit**
- **Win Rate**
- **Max Drawdown**
- **Risk-Reward Ratio**
- **Sharpe Ratio**
- **Total Trades**

---

## Futures Margin Example (NIFTY)

| Index | Lot Size | Price | Value | Margin Rate | Margin Required |
|-------|----------|-------|--------|--------------|------------------|
| NIFTY | 75       | 22,272| ₹16.7L | 11.4%        | ₹1,89,590        |

---

## Margin Types on NSE

- **SPAN Margin**: Based on worst-case risk scenarios.
- **Exposure Margin**: Additional buffer during volatility.

---

## Convergence of Spot and Futures

- Futures prices converge with spot prices as expiry nears.

---

*Document compiled with strategic logic, Pine Script, Python backtesting, and margin calculations.*

