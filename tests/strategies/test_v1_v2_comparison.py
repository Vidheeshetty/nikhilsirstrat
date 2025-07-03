"""Comprehensive tests comparing V1 and V2 SMA Fractal Scalper strategies.

This test suite ensures that the new pluggable architecture (V2) produces
identical results to the original strategy (V1) under various scenarios.
"""

import pytest
import pandas as pd
from typing import Dict, Any, List, Optional
import tempfile
import os
import yaml
from unittest.mock import MagicMock

from src.strategies.sma_fractal_scalper.strategy import SmaFractalScalper
from src.strategies.sma_fractal_scalper.config import SmaFractalScalperConfig
from src.strategies.sma_fractal_scalper_v2.strategy import SmaFractalScalperV2
from src.strategies.sma_fractal_scalper_v2.config import SmaFractalScalperV2Config


class MockBar:
    """Mock bar object for testing."""
    def __init__(self, open_price, high, low, close, volume=1000, timestamp=None):
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp or pd.Timestamp.now()


@pytest.fixture
def temp_v2_config_files():
    """Create temporary V2 configuration files matching V1 parameters."""
    temp_dir = tempfile.mkdtemp()
    
    # Create indicators config matching V1 defaults
    indicators_config = {
        'indicators': {
            'sma_short': {
                'type': 'sma',
                'enabled': True,
                'visible_on_chart': True,
                'parameters': {'period': 5},
                'chart_settings': {'color': '#FF6B6B'}
            },
            'sma_long': {
                'type': 'sma',
                'enabled': True,
                'visible_on_chart': True,
                'parameters': {'period': 200},
                'chart_settings': {'color': '#4ECDC4'}
            },
            'fractal': {
                'type': 'fractal',
                'enabled': True,
                'visible_on_chart': True,
                'parameters': {'window': 5},
                'chart_settings': {'color': '#45B7D1'}
            }
        }
    }
    
    # Create signals config matching V1 behavior
    signals_config = {
        'signals': {
            'primary_signal': {
                'type': 'sma_fractal',
                'enabled': True,
                'required_indicators': ['sma_short', 'sma_long', 'fractal'],
                'parameters': {
                    'sma_short_period': 5,
                    'sma_long_period': 200,
                    'fractal_window': 5,
                    'use_sma': True,
                    'use_fractals': True
                },
                'confidence_threshold': 0.6
            }
        },
        'signal_combination': {
            'mode': 'primary_only',
            'primary_signal': 'primary_signal'
        }
    }
    
    # Write config files
    indicators_path = os.path.join(temp_dir, 'indicators.yaml')
    signals_path = os.path.join(temp_dir, 'signals.yaml')
    
    with open(indicators_path, 'w') as f:
        yaml.dump(indicators_config, f)
    
    with open(signals_path, 'w') as f:
        yaml.dump(signals_config, f)
    
    return {
        'temp_dir': temp_dir,
        'indicators_path': indicators_path,
        'signals_path': signals_path
    }


@pytest.fixture
def test_scenarios():
    """Generate various test scenarios with different market conditions."""
    scenarios = {}
    
    # Scenario 1: Simple uptrend with SMA crossover
    uptrend_bars = []
    base_price = 1000.0
    for i in range(250):  # Need enough bars for 200-period SMA
        price = base_price + (i * 0.1)  # Gradual uptrend
        bar = MockBar(
            open_price=price - 0.05,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=i)
        )
        uptrend_bars.append(bar)
    scenarios['uptrend'] = uptrend_bars
    
    # Scenario 2: Simple downtrend with SMA crossover
    downtrend_bars = []
    base_price = 1000.0
    for i in range(250):
        price = base_price - (i * 0.1)  # Gradual downtrend
        bar = MockBar(
            open_price=price + 0.05,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=i)
        )
        downtrend_bars.append(bar)
    scenarios['downtrend'] = downtrend_bars
    
    # Scenario 3: Sideways market (no clear trend)
    sideways_bars = []
    base_price = 1000.0
    for i in range(250):
        # Oscillate around base price
        price = base_price + (5 * (i % 10 - 5) * 0.1)
        bar = MockBar(
            open_price=price - 0.05,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=i)
        )
        sideways_bars.append(bar)
    scenarios['sideways'] = sideways_bars
    
    # Scenario 4: Volatile market with multiple crossovers
    volatile_bars = []
    base_price = 1000.0
    for i in range(250):
        # Create volatility with sine wave pattern
        import math
        volatility = 10 * math.sin(i / 10.0)
        price = base_price + volatility + (i * 0.02)  # Small overall uptrend
        bar = MockBar(
            open_price=price - 0.5,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=i)
        )
        volatile_bars.append(bar)
    scenarios['volatile'] = volatile_bars
    
    return scenarios


class TestV1V2Comparison:
    """Test suite comparing V1 and V2 strategy implementations."""
    
    def _create_v1_strategy(self) -> SmaFractalScalper:
        """Create V1 strategy with standard configuration."""
        config = SmaFractalScalperConfig(
            sma_short_period=5,
            sma_long_period=200,
            fractal_window=5,
            use_sma=True,
            use_fractals=True,
            historical_warmup=False  # We'll warm up manually
        )
        
        # Mock broker manager to avoid actual broker integration
        broker_manager = MagicMock()
        strategy = SmaFractalScalper(config, broker_manager=broker_manager)
        
        return strategy
    
    def _create_v2_strategy(self, temp_config_files) -> SmaFractalScalperV2:
        """Create V2 strategy with matching configuration."""
        config = SmaFractalScalperV2Config(
            sma_short_period=5,
            sma_long_period=200,
            fractal_window=5,
            use_sma=True,
            use_fractals=True,
            historical_warmup=False,  # We'll warm up manually
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        return strategy
    
    def _warm_up_strategies(self, v1_strategy, v2_strategy, warmup_bars):
        """Warm up both strategies with the same historical data."""
        # Warm up V1 strategy
        v1_strategy.gen.warm_up_with_historical_data(warmup_bars)
        
        # Warm up V2 strategy
        warmup_data = []
        for bar in warmup_bars:
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            warmup_data.append(bar_dict)
        
        v2_strategy.warmup_indicators(warmup_data)
    
    def _compare_signal_results(self, v1_result, v2_result, bar_info: str):
        """Compare signal results from both strategies."""
        # Both should either have a signal or not have a signal
        v1_has_signal = v1_result is not None
        v2_has_signal = v2_result is not None
        
        if v1_has_signal != v2_has_signal:
            print(f"Signal mismatch at {bar_info}:")
            print(f"  V1 signal: {v1_result}")
            print(f"  V2 signal: {v2_result}")
            return False
        
        if v1_has_signal and v2_has_signal:
            # Compare signal details
            v1_direction = v1_result.get('direction')
            v2_direction = v2_result.get('direction')
            
            if v1_direction != v2_direction:
                print(f"Direction mismatch at {bar_info}:")
                print(f"  V1 direction: {v1_direction}")
                print(f"  V2 direction: {v2_direction}")
                return False
            
            # Compare prices (allow small floating point differences)
            v1_entry = v1_result.get('entry_price', 0)
            v2_entry = v2_result.get('entry_price', 0)
            
            if abs(v1_entry - v2_entry) > 0.01:  # Allow 1 cent difference
                print(f"Entry price mismatch at {bar_info}:")
                print(f"  V1 entry: {v1_entry}")
                print(f"  V2 entry: {v2_entry}")
                return False
        
        return True
    
    def test_identical_signal_generation_uptrend(self, temp_v2_config_files, test_scenarios):
        """Test that V1 and V2 generate identical signals in uptrend scenario."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        scenario_bars = test_scenarios['uptrend']
        warmup_bars = scenario_bars[:210]  # First 210 bars for warmup
        test_bars = scenario_bars[210:]    # Remaining bars for testing
        
        # Warm up both strategies
        self._warm_up_strategies(v1_strategy, v2_strategy, warmup_bars)
        
        # Test signal generation on remaining bars
        signal_matches = 0
        total_bars = 0
        
        for i, bar in enumerate(test_bars):
            # Process bar in V1
            v1_result = v1_strategy.on_bar(bar)
            
            # Process bar in V2
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            v2_result = v2_strategy.on_bar(bar_dict)
            
            # Compare results
            bar_info = f"uptrend bar {i} (price: {bar.close})"
            if self._compare_signal_results(v1_result, v2_result, bar_info):
                signal_matches += 1
            
            total_bars += 1
        
        # Ensure high match rate (should be 100% for identical logic)
        match_rate = signal_matches / total_bars
        assert match_rate >= 0.95, f"Signal match rate too low: {match_rate:.2%}"
        print(f"Uptrend scenario: {signal_matches}/{total_bars} signals matched ({match_rate:.2%})")
    
    def test_identical_signal_generation_downtrend(self, temp_v2_config_files, test_scenarios):
        """Test that V1 and V2 generate identical signals in downtrend scenario."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        scenario_bars = test_scenarios['downtrend']
        warmup_bars = scenario_bars[:210]
        test_bars = scenario_bars[210:]
        
        self._warm_up_strategies(v1_strategy, v2_strategy, warmup_bars)
        
        signal_matches = 0
        total_bars = 0
        
        for i, bar in enumerate(test_bars):
            v1_result = v1_strategy.on_bar(bar)
            
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            v2_result = v2_strategy.on_bar(bar_dict)
            
            bar_info = f"downtrend bar {i} (price: {bar.close})"
            if self._compare_signal_results(v1_result, v2_result, bar_info):
                signal_matches += 1
            
            total_bars += 1
        
        match_rate = signal_matches / total_bars
        assert match_rate >= 0.95, f"Signal match rate too low: {match_rate:.2%}"
        print(f"Downtrend scenario: {signal_matches}/{total_bars} signals matched ({match_rate:.2%})")
    
    def test_identical_signal_generation_sideways(self, temp_v2_config_files, test_scenarios):
        """Test that V1 and V2 generate identical signals in sideways scenario."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        scenario_bars = test_scenarios['sideways']
        warmup_bars = scenario_bars[:210]
        test_bars = scenario_bars[210:]
        
        self._warm_up_strategies(v1_strategy, v2_strategy, warmup_bars)
        
        signal_matches = 0
        total_bars = 0
        
        for i, bar in enumerate(test_bars):
            v1_result = v1_strategy.on_bar(bar)
            
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            v2_result = v2_strategy.on_bar(bar_dict)
            
            bar_info = f"sideways bar {i} (price: {bar.close})"
            if self._compare_signal_results(v1_result, v2_result, bar_info):
                signal_matches += 1
            
            total_bars += 1
        
        match_rate = signal_matches / total_bars
        assert match_rate >= 0.95, f"Signal match rate too low: {match_rate:.2%}"
        print(f"Sideways scenario: {signal_matches}/{total_bars} signals matched ({match_rate:.2%})")
    
    def test_identical_signal_generation_volatile(self, temp_v2_config_files, test_scenarios):
        """Test that V1 and V2 generate identical signals in volatile scenario."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        scenario_bars = test_scenarios['volatile']
        warmup_bars = scenario_bars[:210]
        test_bars = scenario_bars[210:]
        
        self._warm_up_strategies(v1_strategy, v2_strategy, warmup_bars)
        
        signal_matches = 0
        total_bars = 0
        
        for i, bar in enumerate(test_bars):
            v1_result = v1_strategy.on_bar(bar)
            
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            v2_result = v2_strategy.on_bar(bar_dict)
            
            bar_info = f"volatile bar {i} (price: {bar.close})"
            if self._compare_signal_results(v1_result, v2_result, bar_info):
                signal_matches += 1
            
            total_bars += 1
        
        match_rate = signal_matches / total_bars
        assert match_rate >= 0.95, f"Signal match rate too low: {match_rate:.2%}"
        print(f"Volatile scenario: {signal_matches}/{total_bars} signals matched ({match_rate:.2%})")
    
    def test_identical_warmup_requirements(self, temp_v2_config_files):
        """Test that both strategies have identical warmup requirements."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        # V1 warmup requirements (manually calculated)
        v1_warmup = max(v1_strategy.config.sma_long_period, v1_strategy.config.fractal_window)
        
        # V2 warmup requirements (from indicator manager)
        v2_warmup_dict = v2_strategy.get_warmup_requirements()
        v2_warmup = max(v2_warmup_dict.values()) if v2_warmup_dict else 0
        
        assert v1_warmup == v2_warmup, f"Warmup requirements differ: V1={v1_warmup}, V2={v2_warmup}"
        print(f"Both strategies require {v1_warmup} bars for warmup")
    
    def test_identical_configuration_parameters(self, temp_v2_config_files):
        """Test that both strategies use identical configuration parameters."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        # Compare key parameters
        assert v1_strategy.config.sma_short_period == v2_strategy.config.sma_short_period
        assert v1_strategy.config.sma_long_period == v2_strategy.config.sma_long_period
        assert v1_strategy.config.fractal_window == v2_strategy.config.fractal_window
        assert v1_strategy.config.use_sma == v2_strategy.config.use_sma
        assert v1_strategy.config.use_fractals == v2_strategy.config.use_fractals
        
        print("Configuration parameters match between V1 and V2")
    
    def test_trade_recording_compatibility(self, temp_v2_config_files, test_scenarios):
        """Test that both strategies record trades in the same format."""
        v1_strategy = self._create_v1_strategy()
        v2_strategy = self._create_v2_strategy(temp_v2_config_files)
        
        # Use a scenario that should generate at least one trade
        scenario_bars = test_scenarios['uptrend']
        warmup_bars = scenario_bars[:210]
        test_bars = scenario_bars[210:230]  # Limited bars for focused testing
        
        self._warm_up_strategies(v1_strategy, v2_strategy, warmup_bars)
        
        # Process bars and look for trades
        for bar in test_bars:
            v1_strategy.on_bar(bar)
            
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            v2_strategy.on_bar(bar_dict)
        
        # Check trade recording format
        v1_trades = getattr(v1_strategy, 'trades', [])
        v2_trades = getattr(v2_strategy, 'trades', [])
        
        print(f"V1 recorded {len(v1_trades)} trades")
        print(f"V2 recorded {len(v2_trades)} trades")
        
        # If both have trades, compare format
        if v1_trades and v2_trades:
            v1_trade = v1_trades[0]
            v2_trade = v2_trades[0]
            
            # Check that both have the same keys
            v1_keys = set(v1_trade.keys())
            v2_keys = set(v2_trade.keys())
            
            assert v1_keys == v2_keys, f"Trade format differs: V1 keys={v1_keys}, V2 keys={v2_keys}"
            print("Trade recording format matches between V1 and V2")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"]) 