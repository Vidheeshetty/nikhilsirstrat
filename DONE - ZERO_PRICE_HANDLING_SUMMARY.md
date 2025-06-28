# Zero Bid/Ask Price Handling in Backtesting Strategy

## Problem Statement

The original strategy was vulnerable to crashes and incorrect behavior when encountering quote ticks with zero or invalid bid/ask prices. This is common in real market data, especially for illiquid options where no quotes exist.

## Issues with Zero Prices

1. **Division by zero errors** when calculating spreads
2. **Incorrect mid-price calculations** (0 + ask) / 2 = ask/2
3. **Strategy logic failures** when using invalid prices for entry/exit decisions
4. **Unrealistic backtesting results** due to processing invalid data

## Solution Implemented

### 1. Added Price Validation Method

```python
def _validate_quote_tick(self, tick: QuoteTick) -> tuple[bool, float, float]:
    """
    Validate quote tick prices and return safe bid/ask values.
    
    Returns:
        tuple: (is_valid, bid_price, ask_price)
    """
    bid_price = float(tick.bid_price)
    ask_price = float(tick.ask_price)
    
    # Check for zero or negative prices
    if bid_price <= 0 or ask_price <= 0:
        return False, bid_price, ask_price
    
    # Check for unreasonable bid/ask spread (>50%)
    if bid_price > 0:
        spread_pct = (ask_price - bid_price) / bid_price * 100
        if spread_pct > 50:
            return False, bid_price, ask_price
    
    # Check for price sanity (options shouldn't be >10000)
    if bid_price > 10000 or ask_price > 10000:
        return False, bid_price, ask_price
    
    return True, bid_price, ask_price
```

### 2. Modified Quote Tick Processing

```python
def on_quote_tick(self, tick: QuoteTick):
    # VALIDATE BID/ASK PRICES - Handle zero or invalid prices
    is_valid, bid_price, ask_price = self._validate_quote_tick(tick)
    if not is_valid:
        self.log.info(f"Skipping tick with invalid prices - bid: {bid_price}, ask: {ask_price}")
        return
    
    # Calculate mid price from bid/ask (now safe since we validated prices)
    price = (bid_price + ask_price) / 2
    
    # ... rest of strategy logic
```

## Validation Rules

The strategy now validates quote ticks using these rules:

1. **Zero/Negative Prices**: Skip ticks where bid ≤ 0 or ask ≤ 0
2. **Unreasonable Spread**: Skip ticks where spread > 50% of bid price
3. **Price Sanity**: Skip ticks where bid or ask > 10,000 (unrealistic for options)
4. **Safe Mid-Price**: Only calculate mid-price after validation

## Benefits

### 1. **Robustness**
- Strategy won't crash on invalid price data
- Graceful handling of illiquid options
- Protection against data errors

### 2. **Realistic Backtesting**
- Only processes valid market quotes
- More accurate simulation of real trading conditions
- Better risk management

### 3. **Debugging**
- Clear logging of skipped ticks
- Easy identification of data quality issues
- Transparent validation process

## Test Results

All validation tests pass:
- ✅ Valid prices (100.0/105.0) → ACCEPTED
- ✅ Zero bid price (0.0/105.0) → REJECTED
- ✅ Zero ask price (100.0/0.0) → REJECTED
- ✅ Both zero prices (0.0/0.0) → REJECTED
- ✅ Negative prices (-10.0/105.0) → REJECTED
- ✅ Unreasonable spread (100.0/160.0) → REJECTED
- ✅ Extremely high prices (15000.0/16000.0) → REJECTED

## Usage

The strategy now automatically handles zero bids/asks by:

1. **Skipping invalid ticks** instead of processing them
2. **Logging skipped ticks** for monitoring
3. **Continuing with valid data** for strategy execution
4. **Maintaining rolling windows** only with valid prices

This ensures your backtesting results are based on realistic, tradeable market conditions rather than invalid data points.

## Configuration

The validation thresholds can be adjusted in the `_validate_quote_tick` method:

- **Spread threshold**: Currently 50% (can be modified)
- **Price sanity limit**: Currently 10,000 (can be modified)
- **Logging level**: Currently INFO (can be changed to DEBUG for more detail) 