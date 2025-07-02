#!/usr/bin/env python3
"""Debug script to isolate the strategy initialization issue."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.strategies.sma_fractal_scalper.config import SmaFractalScalperConfig
from src.strategies.sma_fractal_scalper.strategy import SmaFractalScalper

def test_strategy_init():
    """Test strategy initialization to find the >= error."""
    print("Creating config object...")
    config = SmaFractalScalperConfig(
        sma_short_period=5,
        sma_long_period=200,
        use_fractals=True,
        use_sma=True,
        fractal_window=5,
        historical_warmup=False  # Disable to avoid data loading issues
    )
    
    print(f"Config created: {config}")
    print(f"Config types:")
    print(f"  sma_short_period: {type(config.sma_short_period)} = {config.sma_short_period}")
    print(f"  sma_long_period: {type(config.sma_long_period)} = {config.sma_long_period}")
    print(f"  fractal_window: {type(config.fractal_window)} = {config.fractal_window}")
    
    try:
        print("Initializing strategy...")
        strategy = SmaFractalScalper(config)
        print("✅ Strategy initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Strategy initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_strategy_init() 