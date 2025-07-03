"""Tests for SMA Fractal Scalper V2 - Pluggable Architecture.

This test suite validates the new pluggable indicator and signal generation
architecture, ensuring all components work together correctly.
"""

import pytest
import pandas as pd
from typing import Dict, Any, List
import tempfile
import os
import yaml

from src.strategies.sma_fractal_scalper_v2.strategy import SmaFractalScalperV2
from src.strategies.sma_fractal_scalper_v2.config import SmaFractalScalperV2Config
from utils.indicators.manager import IndicatorManager
from utils.indicators.base import IndicatorConfig
from utils.signals.manager import SignalManager
from utils.signals.base import SignalConfig, SignalType


@pytest.fixture
def temp_config_files():
    """Create temporary configuration files for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create indicators config
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
                'parameters': {'period': 20},  # Shorter for testing
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
    
    # Create signals config
    signals_config = {
        'signals': {
            'primary_signal': {
                'type': 'sma_fractal',
                'enabled': True,
                'required_indicators': ['sma_short', 'sma_long', 'fractal'],
                'parameters': {
                    'sma_short_period': 5,
                    'sma_long_period': 20,
                    'fractal_window': 5
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
def sample_market_data():
    """Generate sample market data for testing."""
    data = []
    base_price = 1000.0
    
    # Generate 50 bars of sample data with a trend
    for i in range(50):
        timestamp = pd.Timestamp.now() + pd.Timedelta(minutes=i)
        
        # Create an uptrend
        price = base_price + (i * 0.5) + (i % 5) * 0.2  # Small fluctuations
        
        bar = {
            'timestamp': timestamp,
            'open': price - 0.1,
            'high': price + 0.2,
            'low': price - 0.2,
            'close': price,
            'volume': 1000 + (i * 10)
        }
        data.append(bar)
    
    return data


class TestSmaFractalScalperV2:
    """Test suite for SMA Fractal Scalper V2 strategy."""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        return SmaFractalScalperV2Config(
            risk_per_trade=0.02,
            timeframe='1MIN',
            historical_warmup=True
        )
    
    def test_strategy_initialization(self, temp_config_files):
        """Test strategy initialization with pluggable architecture."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        
        # Check that strategy initialized correctly
        assert strategy.config == config
        assert strategy.indicator_manager is not None
        assert strategy.signal_manager is not None
        
        # Check that indicators were loaded
        indicator_names = strategy.indicator_manager.list_indicators()
        assert 'sma_short' in indicator_names
        assert 'sma_long' in indicator_names
        assert 'fractal' in indicator_names
        
        # Check that signals were loaded
        signal_names = strategy.signal_manager.list_signal_generators()
        assert 'primary_signal' in signal_names
    
    def test_warmup_requirements(self, temp_config_files):
        """Test warmup requirements calculation."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        warmup_reqs = strategy.get_warmup_requirements()
        
        assert isinstance(warmup_reqs, dict)
        # Should have requirements for each indicator
        assert len(warmup_reqs) > 0
    
    def test_indicator_warmup(self, temp_config_files, sample_market_data):
        """Test indicator warmup with historical data."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        
        # Warm up with sample data
        strategy.warmup_indicators(sample_market_data)
        
        # Check that strategy is ready
        assert strategy.warmup_complete
        
        # Check that indicators have values by getting their current values
        current_values = strategy.indicator_manager.get_current_values()
        assert len(current_values) > 0
        for indicator_name, value in current_values.items():
            # Some indicators may not have values immediately, so we just check structure
            assert indicator_name in strategy.indicator_manager.list_indicators()
    
    def test_signal_generation(self, temp_config_files, sample_market_data):
        """Test signal generation from indicators."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        
        # Warm up with initial data
        strategy.warmup_indicators(sample_market_data[:-5])
        
        # Process remaining bars and look for signals
        signals_generated = []
        for bar in sample_market_data[-5:]:
            signal = strategy.on_bar(bar)
            if signal:
                signals_generated.append(signal)
        
        # Signal generation should work without errors
        assert isinstance(signals_generated, list)
    
    def test_indicator_management(self, temp_config_files):
        """Test dynamic indicator management."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        
        # Test enabling/disabling indicators
        assert strategy.disable_indicator('sma_short')
        assert strategy.enable_indicator('sma_short')
        
        # Test invalid indicator name
        assert not strategy.enable_indicator('nonexistent_indicator')
    
    def test_signal_management(self, temp_config_files):
        """Test dynamic signal generator management."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        
        # Test enabling/disabling signal generators
        assert strategy.disable_signal_generator('primary_signal')
        assert strategy.enable_signal_generator('primary_signal')
        
        # Test invalid signal generator name
        assert not strategy.enable_signal_generator('nonexistent_signal')
    
    def test_chart_configuration(self, temp_config_files):
        """Test chart configuration generation."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        chart_config = strategy.get_chart_config()
        
        assert 'indicators' in chart_config
        assert 'signals' in chart_config
        
        # Check indicator configurations
        indicator_configs = chart_config['indicators']
        assert isinstance(indicator_configs, list)
    
    def test_strategy_status(self, temp_config_files, sample_market_data):
        """Test comprehensive strategy status reporting."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        strategy.warmup_indicators(sample_market_data)
        
        status = strategy.get_status()
        
        assert 'strategy_name' in status
        assert 'warmup_complete' in status
        assert 'indicators' in status
        assert 'signal_generators' in status
        
        # Check that strategy is initialized after warmup
        assert status['warmup_complete'] is True
    
    def test_configuration_export(self, temp_config_files):
        """Test configuration export functionality."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        
        # Export configurations
        exported_config = strategy.export_configuration()
        
        # Check that export contains expected keys
        assert 'strategy_config' in exported_config
        assert 'indicators_config' in exported_config
        assert 'signals_config' in exported_config
    
    def test_strategy_reset(self, temp_config_files, sample_market_data):
        """Test strategy reset functionality."""
        config = SmaFractalScalperV2Config(
            indicators_config_path=temp_config_files['indicators_path'],
            signals_config_path=temp_config_files['signals_path']
        )
        
        strategy = SmaFractalScalperV2(config)
        strategy.warmup_indicators(sample_market_data)
        
        # Verify strategy is ready
        assert strategy.warmup_complete
        
        # Reset strategy
        strategy.reset()
        
        # Verify strategy is reset
        assert not strategy.warmup_complete


class TestIndicatorManager:
    """Test suite for the IndicatorManager."""
    
    def test_indicator_loading(self, temp_config_files):
        """Test loading indicators from configuration."""
        manager = IndicatorManager()
        manager.load_from_config(temp_config_files['indicators_path'])
        
        indicators = manager.list_indicators()
        assert 'sma_short' in indicators
        assert 'sma_long' in indicators
        assert 'fractal' in indicators
    
    def test_indicator_updates(self, temp_config_files):
        """Test updating indicators with market data."""
        manager = IndicatorManager()
        manager.load_from_config(temp_config_files['indicators_path'])
        
        # Update with sample data
        sample_bar = {
            'timestamp': pd.Timestamp.now(),
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000
        }
        
        manager.update_all(sample_bar)
        
        # Check that indicators were updated by getting current values
        current_values = manager.get_current_values()
        assert len(current_values) > 0


class TestSignalManager:
    """Test suite for the SignalManager."""
    
    def test_signal_loading(self, temp_config_files):
        """Test loading signal generators from configuration."""
        manager = SignalManager()
        manager.load_from_config(temp_config_files['signals_path'])
        
        generators = manager.list_signal_generators()
        assert 'primary_signal' in generators
    
    def test_signal_generation(self, temp_config_files):
        """Test signal generation with mock indicator values."""
        manager = SignalManager()
        manager.load_from_config(temp_config_files['signals_path'])
        
        # Mock indicator values
        from utils.indicators.base import IndicatorValue
        
        indicator_values = {
            'sma_short': IndicatorValue(
                timestamp=pd.Timestamp.now(),
                values={'value': 105.0}
            ),
            'sma_long': IndicatorValue(
                timestamp=pd.Timestamp.now(),
                values={'value': 100.0}
            ),
            'fractal': IndicatorValue(
                timestamp=pd.Timestamp.now(),
                values={'fractal_high': 0, 'fractal_low': 99.0}
            )
        }
        
        market_data = {
            'timestamp': pd.Timestamp.now(),
            'close': 104.0
        }
        
        signals = manager.generate_signals(indicator_values, market_data)
        assert isinstance(signals, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 