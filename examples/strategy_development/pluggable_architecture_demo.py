#!/usr/bin/env python3
"""
Demonstration of the Pluggable Indicator and Signal Architecture

This script demonstrates the new pluggable architecture implemented in
SMA Fractal Scalper V2, showing how indicators and signals can be
configured, managed, and visualized independently.

Usage:
    python3 examples/strategy_development/pluggable_architecture_demo.py
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.sma_fractal_scalper_v2.strategy import SmaFractalScalperV2
from src.strategies.sma_fractal_scalper_v2.config import SmaFractalScalperV2Config
from utils.indicators.manager import IndicatorManager
from utils.indicators.base import IndicatorConfig
from utils.signals.manager import SignalManager
from utils.signals.base import SignalConfig, SignalType


def generate_sample_market_data(num_bars: int = 100) -> List[Dict[str, Any]]:
    """Generate realistic sample market data for demonstration."""
    print(f"🔄 Generating {num_bars} bars of sample market data...")
    
    data = []
    base_price = 1000.0
    volatility = 2.0
    trend = 0.02  # Small upward trend
    
    for i in range(num_bars):
        timestamp = pd.Timestamp.now() + pd.Timedelta(minutes=i)
        
        # Add trend and random walk
        price_change = trend + np.random.normal(0, volatility)
        base_price += price_change
        
        # Create OHLC with some intrabar movement
        open_price = base_price
        high_price = base_price + abs(np.random.normal(0, volatility/2))
        low_price = base_price - abs(np.random.normal(0, volatility/2))
        close_price = base_price + np.random.normal(0, volatility/4)
        
        bar = {
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(max(open_price, high_price, close_price), 2),
            'low': round(min(open_price, low_price, close_price), 2),
            'close': round(close_price, 2),
            'volume': int(1000 + np.random.normal(0, 200))
        }
        data.append(bar)
        base_price = close_price
    
    print(f"✅ Generated market data: ${data[0]['close']:.2f} → ${data[-1]['close']:.2f}")
    return data


def demonstrate_indicator_manager():
    """Demonstrate the standalone indicator manager."""
    print("\n" + "="*60)
    print("🔧 INDICATOR MANAGER DEMONSTRATION")
    print("="*60)
    
    # Create indicator manager
    manager = IndicatorManager()
    
    # Add indicators programmatically
    print("\n📊 Adding indicators programmatically...")
    
    # SMA Short
    sma_short_config = IndicatorConfig(
        name="sma_5",
        indicator_type="sma",
        parameters={"period": 5},
        chart_settings={"color": "#FF6B6B", "line_width": 2}
    )
    manager.add_indicator(sma_short_config)
    
    # SMA Long
    sma_long_config = IndicatorConfig(
        name="sma_20",
        indicator_type="sma", 
        parameters={"period": 20},
        chart_settings={"color": "#4ECDC4", "line_width": 2}
    )
    manager.add_indicator(sma_long_config)
    
    # Fractal
    fractal_config = IndicatorConfig(
        name="fractal",
        indicator_type="fractal",
        parameters={"window": 5},
        chart_settings={"color": "#45B7D1", "line_style": "dotted"}
    )
    manager.add_indicator(fractal_config)
    
    # RSI
    rsi_config = IndicatorConfig(
        name="rsi",
        indicator_type="rsi",
        parameters={"period": 14},
        chart_settings={"color": "#FFEAA7", "overlay": False}
    )
    manager.add_indicator(rsi_config)
    
    print(f"✅ Added indicators: {manager.list_indicators()}")
    print(f"📈 Warmup requirements: {manager.get_warmup_requirements()}")
    print(f"🎯 Max warmup needed: {manager.get_max_warmup_requirement()} bars")
    
    # Generate sample data and update indicators
    sample_data = generate_sample_market_data(50)
    
    print(f"\n🔄 Updating indicators with {len(sample_data)} bars...")
    for i, bar in enumerate(sample_data):
        results = manager.update_all(bar)
        
        if i % 10 == 0 or i == len(sample_data) - 1:
            ready_count = sum(1 for ind in manager._indicators.values() if ind.is_ready())
            print(f"   Bar {i+1:2d}: {ready_count}/{len(manager._indicators)} indicators ready")
    
    # Show final indicator values
    print(f"\n📊 Final indicator values:")
    current_values = manager.get_current_values()
    for name, value in current_values.items():
        if value:
            main_val = value.get_main_value()
            if main_val is not None:
                print(f"   {name:10s}: {main_val:8.2f}")
            else:
                print(f"   {name:10s}: {value.values}")
        else:
            print(f"   {name:10s}: Not ready")
    
    # Show chart configurations
    print(f"\n🎨 Chart configurations:")
    chart_configs = manager.get_chart_configs()
    for config in chart_configs:
        print(f"   {config['name']:10s}: {config['settings']['color']} "
              f"({'overlay' if config['overlay'] else 'separate pane'})")
    
    return manager


def demonstrate_signal_manager(indicator_manager: IndicatorManager):
    """Demonstrate the standalone signal manager."""
    print("\n" + "="*60)
    print("🎯 SIGNAL MANAGER DEMONSTRATION")
    print("="*60)
    
    # Create signal manager
    signal_manager = SignalManager()
    
    # Add signal generators programmatically
    print("\n⚡ Adding signal generators...")
    
    # SMA Fractal Signal
    sma_fractal_config = SignalConfig(
        name="sma_fractal_signal",
        signal_type="sma_fractal",
        required_indicators=["sma_5", "sma_20", "fractal"],
        parameters={
            "sma_short_period": 5,
            "sma_long_period": 20,
            "fractal_window": 5
        },
        confidence_threshold=0.7
    )
    signal_manager.add_signal_generator(sma_fractal_config)
    
    # RSI Bollinger Signal (if we had Bollinger Bands)
    # For demo, we'll create a simpler RSI-based signal
    
    print(f"✅ Added signal generators: {signal_manager.list_signal_generators()}")
    
    # Generate signals using current indicator values
    print(f"\n🔄 Generating signals...")
    
    sample_data = generate_sample_market_data(10)
    signals_generated = []
    
    for i, bar in enumerate(sample_data):
        # Update indicators
        indicator_values = indicator_manager.update_all(bar)
        
        # Generate signals
        signals = signal_manager.generate_signals(indicator_values, bar)
        combined_signal = signal_manager.get_combined_signal()
        
        if combined_signal and combined_signal.is_actionable():
            signals_generated.append(combined_signal)
            print(f"   Bar {i+1}: {combined_signal.signal_type.value.upper()} "
                  f"(confidence: {combined_signal.confidence:.2f})")
            print(f"            Reasons: {'; '.join(combined_signal.reasons[:2])}")
    
    if not signals_generated:
        print("   No actionable signals generated in this sample")
    
    # Show signal manager status
    print(f"\n📊 Signal manager status:")
    status = signal_manager.get_status()
    for name, gen_status in status["signal_generators"].items():
        print(f"   {name}: enabled={gen_status['enabled']}, "
              f"signals={gen_status['signal_count']}")
    
    return signal_manager


def demonstrate_full_strategy():
    """Demonstrate the complete pluggable strategy."""
    print("\n" + "="*60)
    print("🚀 COMPLETE STRATEGY DEMONSTRATION")
    print("="*60)
    
    # Note: For this demo, we'll create temporary config files
    import tempfile
    import yaml
    
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")
    
    # Create indicators config
    indicators_config = {
        'indicators': {
            'sma_short': {
                'type': 'sma',
                'enabled': True,
                'visible_on_chart': True,
                'parameters': {'period': 5},
                'chart_settings': {'color': '#FF6B6B', 'line_width': 2}
            },
            'sma_long': {
                'type': 'sma',
                'enabled': True,
                'visible_on_chart': True,
                'parameters': {'period': 20},
                'chart_settings': {'color': '#4ECDC4', 'line_width': 2}
            },
            'fractal': {
                'type': 'fractal',
                'enabled': True,
                'visible_on_chart': True,
                'parameters': {'window': 5},
                'chart_settings': {'color': '#45B7D1', 'line_style': 'dotted'}
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
    
    # Create strategy configuration
    config = SmaFractalScalperV2Config(
        risk_per_trade=0.02,
        timeframe='1MIN',
        indicators_config_path=indicators_path,
        signals_config_path=signals_path,
        historical_warmup=True
    )
    
    print(f"\n🔧 Initializing SMA Fractal Scalper V2...")
    strategy = SmaFractalScalperV2(config)
    
    print(f"✅ Strategy initialized")
    print(f"   Indicators loaded: {strategy.indicator_manager.list_indicators()}")
    print(f"   Signals loaded: {strategy.signal_manager.list_signal_generators()}")
    
    # Get warmup requirements
    warmup_reqs = strategy.get_warmup_requirements()
    print(f"\n📊 Warmup requirements: {warmup_reqs['max_warmup_bars']} bars")
    
    # Generate historical data for warmup
    historical_data = generate_sample_market_data(warmup_reqs['max_warmup_bars'] + 10)
    warmup_data = historical_data[:-10]
    live_data = historical_data[-10:]
    
    print(f"\n🔄 Warming up with {len(warmup_data)} historical bars...")
    strategy.warm_up_indicators(warmup_data)
    
    if strategy.is_ready():
        print(f"✅ Strategy ready for trading!")
    else:
        print(f"⚠️ Strategy not ready - check indicator status")
    
    # Process live data
    print(f"\n📈 Processing {len(live_data)} live bars...")
    signals_generated = []
    
    for i, bar in enumerate(live_data):
        signal = strategy.on_bar(bar)
        
        # Get current indicator values
        indicator_values = strategy.get_current_indicator_values()
        
        print(f"\n   Bar {i+1} @ ${bar['close']:.2f}:")
        print(f"      SMA(5): {indicator_values.get('sma_short', 'N/A'):.2f}")
        print(f"      SMA(20): {indicator_values.get('sma_long', 'N/A'):.2f}")
        
        if signal and signal.is_actionable():
            signals_generated.append(signal)
            print(f"      🎯 SIGNAL: {signal.signal_type.value.upper()} "
                  f"(confidence: {signal.confidence:.2f})")
            print(f"         Reasons: {signal.reasons[0] if signal.reasons else 'No reasons'}")
        else:
            print(f"      📊 No actionable signal")
    
    # Show final strategy status
    print(f"\n📊 Final Strategy Status:")
    status = strategy.get_strategy_status()
    print(f"   Strategy: {status['strategy_name']}")
    print(f"   Initialized: {status['initialized']}")
    print(f"   Ready: {strategy.is_ready()}")
    print(f"   Signals generated: {len(signals_generated)}")
    
    if signals_generated:
        print(f"\n🎯 Signals Summary:")
        for i, signal in enumerate(signals_generated):
            print(f"   {i+1}. {signal.signal_type.value.upper()} @ ${signal.price:.2f} "
                  f"(confidence: {signal.confidence:.2f})")
    
    # Demonstrate dynamic configuration
    print(f"\n🔧 Dynamic Configuration Demo:")
    print(f"   Disabling SMA short indicator...")
    strategy.disable_indicator('sma_short')
    
    print(f"   Re-enabling SMA short indicator...")
    strategy.enable_indicator('sma_short')
    
    print(f"   Toggling fractal chart visibility...")
    strategy.toggle_indicator_visibility('fractal')
    
    # Show chart configuration
    print(f"\n🎨 Chart Configuration:")
    chart_config = strategy.get_chart_configuration()
    for indicator in chart_config['indicators']:
        visibility = "visible" if indicator['visible'] else "hidden"
        print(f"   {indicator['name']:12s}: {indicator['settings']['color']} ({visibility})")
    
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)
    print(f"\n🧹 Cleaned up temporary files")
    
    return strategy


def main():
    """Main demonstration function."""
    print("🎯 PLUGGABLE INDICATOR & SIGNAL ARCHITECTURE DEMONSTRATION")
    print("=" * 80)
    print("This demo shows the new pluggable architecture that separates:")
    print("• Indicator calculations (SMA, Fractal, RSI, etc.)")
    print("• Signal generation logic (combining indicators)")
    print("• Strategy execution (position management)")
    print("• Chart visualization (configurable display)")
    
    try:
        # Demonstrate individual components
        indicator_manager = demonstrate_indicator_manager()
        signal_manager = demonstrate_signal_manager(indicator_manager)
        
        # Demonstrate complete strategy
        strategy = demonstrate_full_strategy()
        
        print("\n" + "="*80)
        print("✅ DEMONSTRATION COMPLETE!")
        print("="*80)
        print("Key Benefits Demonstrated:")
        print("• ✅ Pluggable indicators with configuration-driven management")
        print("• ✅ Separable signal generation logic")
        print("• ✅ Dynamic enable/disable of components")
        print("• ✅ Chart visualization configuration")
        print("• ✅ Comprehensive testing capabilities")
        print("• ✅ Easy reusability across strategies")
        
        print(f"\nNext Steps:")
        print(f"• Run tests: pytest tests/strategies/test_sma_fractal_scalper_v2.py")
        print(f"• Customize indicators: Edit src/strategies/sma_fractal_scalper_v2/indicators.yaml")
        print(f"• Customize signals: Edit src/strategies/sma_fractal_scalper_v2/signals.yaml")
        print(f"• Create new indicators: Add to utils/indicators/implementations.py")
        print(f"• Create new signals: Add to utils/signals/implementations.py")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 