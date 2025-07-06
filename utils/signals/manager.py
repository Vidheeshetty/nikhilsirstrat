"""Signal manager for coordinating multiple signal generators.

This module provides a manager class that handles multiple signal generators,
their lifecycle, and provides unified signal combination logic.
"""

from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

from .base import BaseSignalGenerator, SignalConfig, TradingSignal, SignalType
from .registry import signal_registry
from utils.indicators.base import IndicatorValue


class SignalManager:
    """Manager for coordinating multiple signal generators."""
    
    def __init__(self):
        self._signal_generators: Dict[str, BaseSignalGenerator] = {}
        self._enabled_generators: Dict[str, BaseSignalGenerator] = {}
        self._combination_config: Dict[str, Any] = {}
        self._last_signals: Dict[str, TradingSignal] = {}
        
    def load_from_config(self, config_path: str) -> None:
        """Load signal generators from configuration file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Load signal generators
        signals_config = config_data.get('signals', {})
        for signal_name, signal_data in signals_config.items():
            self.add_signal_generator_from_dict(signal_name, signal_data)
        
        # Load combination configuration
        self._combination_config = config_data.get('signal_combination', {
            'mode': 'primary_only',
            'primary_signal': list(signals_config.keys())[0] if signals_config else None
        })
    
    def add_signal_generator_from_dict(self, name: str, config_dict: Dict[str, Any]) -> bool:
        """Add signal generator from dictionary configuration.
        
        Args:
            name: Unique name for this signal generator instance
            config_dict: Dictionary containing signal generator configuration
            
        Returns:
            True if signal generator added successfully, False otherwise
        """
        try:
            config = SignalConfig(
                name=name,
                signal_type=config_dict['type'],
                enabled=config_dict.get('enabled', True),
                required_indicators=config_dict.get('required_indicators', []),
                parameters=config_dict.get('parameters', {}),
                confidence_threshold=config_dict.get('confidence_threshold', 0.5)
            )
            
            return self.add_signal_generator(config)
            
        except Exception as e:
            print(f"Failed to add signal generator {name}: {e}")
            return False
    
    def add_signal_generator(self, config: SignalConfig) -> bool:
        """Add a signal generator to the manager.
        
        Args:
            config: Signal generator configuration
            
        Returns:
            True if signal generator added successfully, False otherwise
        """
        signal_generator = signal_registry.create_signal_generator(config)
        if not signal_generator:
            return False
        
        self._signal_generators[config.name] = signal_generator
        
        # Add to enabled generators if enabled
        if config.enabled:
            self._enabled_generators[config.name] = signal_generator
            
        print(f"Added signal generator: {config.name} ({config.signal_type})")
        return True
    
    def remove_signal_generator(self, name: str) -> bool:
        """Remove a signal generator from the manager.
        
        Args:
            name: Name of the signal generator to remove
            
        Returns:
            True if signal generator removed successfully, False otherwise
        """
        if name in self._signal_generators:
            del self._signal_generators[name]
            if name in self._enabled_generators:
                del self._enabled_generators[name]
            if name in self._last_signals:
                del self._last_signals[name]
            print(f"Removed signal generator: {name}")
            return True
        return False
    
    def enable_signal_generator(self, name: str) -> bool:
        """Enable a signal generator.
        
        Args:
            name: Name of the signal generator to enable
            
        Returns:
            True if signal generator enabled successfully, False otherwise
        """
        if name in self._signal_generators:
            signal_generator = self._signal_generators[name]
            signal_generator.enabled = True
            self._enabled_generators[name] = signal_generator
            print(f"Enabled signal generator: {name}")
            return True
        return False
    
    def disable_signal_generator(self, name: str) -> bool:
        """Disable a signal generator.
        
        Args:
            name: Name of the signal generator to disable
            
        Returns:
            True if signal generator disabled successfully, False otherwise
        """
        if name in self._signal_generators:
            signal_generator = self._signal_generators[name]
            signal_generator.enabled = False
            if name in self._enabled_generators:
                del self._enabled_generators[name]
            print(f"Disabled signal generator: {name}")
            return True
        return False
    
    def generate_signals(
        self, 
        indicator_values: Dict[str, IndicatorValue],
        market_data: Dict[str, float]
    ) -> Dict[str, TradingSignal]:
        """Generate signals from all enabled signal generators.
        
        Args:
            indicator_values: Dictionary mapping indicator names to their current values
            market_data: Dictionary containing current OHLCV data
            
        Returns:
            Dictionary mapping signal generator names to their generated signals
        """
        signals = {}
        
        for name, signal_generator in self._enabled_generators.items():
            try:
                signal = signal_generator.generate_signal(indicator_values, market_data)
                if signal:
                    signals[name] = signal
                    self._last_signals[name] = signal
            except Exception as e:
                print(f"Error generating signal from {name}: {e}")
        
        return signals
    
    def get_combined_signal(self) -> Optional[TradingSignal]:
        """Get combined signal based on combination configuration.
        
        Returns:
            Combined TradingSignal if available, None otherwise
        """
        if not self._last_signals:
            return None
        
        combination_mode = self._combination_config.get('mode', 'primary_only')
        
        if combination_mode == 'primary_only':
            primary_signal_name = self._combination_config.get('primary_signal')
            if primary_signal_name and primary_signal_name in self._last_signals:
                return self._last_signals[primary_signal_name]
        
        elif combination_mode == 'all_agree':
            return self._combine_signals_all_agree()
        
        elif combination_mode == 'weighted_average':
            return self._combine_signals_weighted()
        
        return None
    
    def _combine_signals_all_agree(self) -> Optional[TradingSignal]:
        """Combine signals requiring all to agree."""
        if not self._last_signals:
            return None
        
        actionable_signals = [signal for signal in self._last_signals.values() 
                            if signal.is_actionable()]
        
        if not actionable_signals:
            return None
        
        # Check if all signals agree on direction
        signal_types = [signal.signal_type for signal in actionable_signals]
        if len(set(signal_types)) == 1:
            # All agree - combine confidence
            avg_confidence = sum(signal.confidence for signal in actionable_signals) / len(actionable_signals)
            combined_reasons = []
            for signal in actionable_signals:
                combined_reasons.extend(signal.reasons)
            
            return TradingSignal(
                signal_type=signal_types[0],
                timestamp=actionable_signals[0].timestamp,
                confidence=min(0.95, avg_confidence),
                price=actionable_signals[0].price,
                reasons=combined_reasons,
                metadata={"combination_mode": "all_agree", "signal_count": len(actionable_signals)}
            )
        
        return None
    
    def _combine_signals_weighted(self) -> Optional[TradingSignal]:
        """Combine signals using weighted average."""
        if not self._last_signals:
            return None
        
        weights = self._combination_config.get('weights', {})
        min_confidence = self._combination_config.get('min_combined_confidence', 0.7)
        
        total_weight = 0
        weighted_confidence = 0
        signal_votes = {'long': 0, 'short': 0, 'hold': 0}
        combined_reasons = []
        
        for name, signal in self._last_signals.items():
            weight = weights.get(name, 1.0)
            total_weight += weight
            weighted_confidence += signal.confidence * weight
            
            # Vote based on signal type and confidence
            if signal.signal_type == SignalType.LONG:
                signal_votes['long'] += weight * signal.confidence
            elif signal.signal_type == SignalType.SHORT:
                signal_votes['short'] += weight * signal.confidence
            else:
                signal_votes['hold'] += weight * signal.confidence
            
            combined_reasons.extend([f"{name}: {reason}" for reason in signal.reasons])
        
        if total_weight == 0:
            return None
        
        # Normalize
        final_confidence = weighted_confidence / total_weight
        for vote_type in signal_votes:
            signal_votes[vote_type] /= total_weight
        
        # Determine final signal
        max_vote = max(signal_votes.values())
        if max_vote < min_confidence:
            final_signal_type = SignalType.HOLD
        else:
            final_signal_type = SignalType.LONG if signal_votes['long'] == max_vote else \
                               SignalType.SHORT if signal_votes['short'] == max_vote else \
                               SignalType.HOLD
        
        return TradingSignal(
            signal_type=final_signal_type,
            timestamp=list(self._last_signals.values())[0].timestamp,
            confidence=final_confidence,
            price=list(self._last_signals.values())[0].price,
            reasons=combined_reasons,
            metadata={
                "combination_mode": "weighted_average",
                "votes": signal_votes,
                "weights": weights
            }
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get status information for all signal generators.
        
        Returns:
            Dictionary containing status information
        """
        return {
            "signal_generators": {
                name: signal_generator.get_status()
                for name, signal_generator in self._signal_generators.items()
            },
            "combination_config": self._combination_config,
            "last_combined_signal": {
                "type": self.get_combined_signal().signal_type.value if self.get_combined_signal() else None,
                "confidence": self.get_combined_signal().confidence if self.get_combined_signal() else None
            }
        }
    
    def get_chart_configs(self) -> List[Dict[str, Any]]:
        """Get chart configurations for signal visualization.
        
        Returns:
            List of chart configuration dictionaries
        """
        # This could be extended to provide signal visualization configs
        return []
    
    def reset_all(self) -> None:
        """Reset all signal generators."""
        for signal_generator in self._signal_generators.values():
            signal_generator.reset()
        self._last_signals.clear()
        print("Reset all signal generators")
    
    def get_signal_generator(self, name: str) -> Optional[BaseSignalGenerator]:
        """Get a specific signal generator by name.
        
        Args:
            name: Name of the signal generator
            
        Returns:
            Signal generator instance if found, None otherwise
        """
        return self._signal_generators.get(name)
    
    def list_signal_generators(self) -> List[str]:
        """Get list of all signal generator names.
        
        Returns:
            List of signal generator names
        """
        return list(self._signal_generators.keys())
    
    def list_enabled_signal_generators(self) -> List[str]:
        """Get list of enabled signal generator names.
        
        Returns:
            List of enabled signal generator names
        """
        return list(self._enabled_generators.keys())
    
    def has_enabled_generators(self) -> bool:
        """Check if there are any enabled signal generators.
        
        Returns:
            True if there are enabled generators, False otherwise
        """
        return len(self._enabled_generators) > 0
    
    def export_config(self, config_path: str) -> None:
        """Export current signal configuration to file.
        
        Args:
            config_path: Path to save configuration file
        """
        config_data = {
            'signals': {},
            'signal_combination': self._combination_config
        }
        
        for name, signal_generator in self._signal_generators.items():
            config_data['signals'][name] = {
                'type': signal_generator.signal_type,
                'enabled': signal_generator.enabled,
                'required_indicators': signal_generator.required_indicators,
                'parameters': signal_generator.parameters,
                'confidence_threshold': signal_generator.confidence_threshold
            }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
        
        print(f"Exported signal configuration to: {config_path}") 