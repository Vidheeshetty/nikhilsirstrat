#!/usr/bin/env python3
"""
Test script to verify that the strategy properly handles zero bid/ask prices.
"""

import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos

# Import the strategy
from src.strategies.my_nse_strategy.strategy import MyNSEStrategy
from src.strategies.my_nse_strategy.config import MyNSEStrategyConfig

def test_zero_price_handling():
    """Test that the strategy properly handles zero bid/ask prices."""
    
    print("Testing strategy zero price handling...")
    print("=" * 50)
    
    # Create a test configuration
    config = MyNSEStrategyConfig(
        instrument_id=InstrumentId(symbol=Symbol("NIFTY.OPT.03Jul2025.22800.CALL"), venue=Venue("NSE")),
        lookback_intervals=5,
        entry_buffer_pct=1.0,
        min_iv=0.1,
        min_oi_change=100,
        tp_pct=5.0,
        breakeven_trigger_pct=2.0,
        position_size=1,
        meta_catalog_path="catalog-data/my_nse_strategy/catalog-meta"
    )
    
    # Create strategy instance
    strategy = MyNSEStrategy(config)
    
    # Test cases with different price scenarios
    test_cases = [
        {
            "name": "Valid prices",
            "bid": 100.0,
            "ask": 105.0,
            "expected_valid": True
        },
        {
            "name": "Zero bid price",
            "bid": 0.0,
            "ask": 105.0,
            "expected_valid": False
        },
        {
            "name": "Zero ask price",
            "bid": 100.0,
            "ask": 0.0,
            "expected_valid": False
        },
        {
            "name": "Both zero prices",
            "bid": 0.0,
            "ask": 0.0,
            "expected_valid": False
        },
        {
            "name": "Negative bid price",
            "bid": -10.0,
            "ask": 105.0,
            "expected_valid": False
        },
        {
            "name": "Unreasonable spread (>50%)",
            "bid": 100.0,
            "ask": 160.0,  # 60% spread
            "expected_valid": False
        },
        {
            "name": "Extremely high prices",
            "bid": 15000.0,
            "ask": 16000.0,
            "expected_valid": False
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"  Bid: {test_case['bid']}, Ask: {test_case['ask']}")
        
        # Create a mock QuoteTick
        tick = QuoteTick(
            instrument_id=config.instrument_id,
            ts_event=dt_to_unix_nanos(datetime.now(timezone.utc)),
            ts_init=dt_to_unix_nanos(datetime.now(timezone.utc)),
            bid_price=Price(test_case['bid'], 2),
            ask_price=Price(test_case['ask'], 2),
            bid_size=Quantity(100, 0),
            ask_size=Quantity(100, 0)
        )
        
        # Test the validation method
        is_valid, bid_price, ask_price = strategy._validate_quote_tick(tick)
        
        print(f"  Expected valid: {test_case['expected_valid']}")
        print(f"  Actual valid: {is_valid}")
        print(f"  Result: {'✓ PASS' if is_valid == test_case['expected_valid'] else '✗ FAIL'}")
        
        if is_valid != test_case['expected_valid']:
            print(f"  ERROR: Validation failed for {test_case['name']}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_zero_price_handling() 