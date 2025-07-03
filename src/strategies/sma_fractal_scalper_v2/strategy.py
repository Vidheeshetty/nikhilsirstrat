"""SMA Fractal Scalper V2 - Pluggable Architecture Implementation.

This strategy demonstrates the new pluggable indicator and signal generation
architecture, separating concerns for better testability and reusability.
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd

from utils.strategy.base_strategy import BaseStrategy
from utils.indicators.manager import IndicatorManager
from utils.signals.manager import SignalManager
from utils.signals.base import TradingSignal, SignalType
from .config import SmaFractalScalperV2Config


class SmaFractalScalperV2(BaseStrategy):
    """SMA Fractal Scalper V2 with pluggable architecture."""
    
    def __init__(self, config: SmaFractalScalperV2Config):
        """Initialize the SMA Fractal Scalper V2 strategy."""
        super().__init__(config)
        
        # Initialize managers
        self.indicator_manager = IndicatorManager()
        self.signal_manager = SignalManager()
        
        # Strategy state (V1 compatibility)
        self.position: str = None  # "LONG", "SHORT", or None
        self.trades: list = []  # Store completed trades
        self._entry_price: float = None
        self._stop_price: float = None
        self._entry_ts: Any = None
        self._entry_oi: float = None
        self._last_price: float = None
        
        # Pluggable architecture state
        self.warmup_complete = False
        self.last_signal = None
        
        # Load configurations
        self._load_configurations()
        
        self.log.info("SmaFractalScalperV2 initialized with pluggable architecture")
    
    def _load_configurations(self) -> None:
        """Load indicator and signal configurations."""
        try:
            # Load indicators
            self.indicator_manager.load_from_config(self.config.indicators_config_path)
            self.log.info(f"Loaded indicators: {self.indicator_manager.list_indicators()}")
            
            # Load signals
            self.signal_manager.load_from_config(self.config.signals_config_path)
            self.log.info(f"Loaded signals: {self.signal_manager.list_signal_generators()}")
            
            # Validate that signal generators have required indicators
            available_indicators = self.indicator_manager.list_indicators()
            for signal_name in self.signal_manager.list_signal_generators():
                signal_gen = self.signal_manager.get_signal_generator(signal_name)
                if signal_gen and not signal_gen.can_generate_signal(available_indicators):
                    missing = [ind for ind in signal_gen.required_indicators 
                             if ind not in available_indicators]
                    self.log.warning(f"Signal generator {signal_name} missing indicators: {missing}")
            
        except Exception as e:
            self.log.error(f"Failed to load configurations: {e}")
            raise
    
    def get_warmup_requirements(self) -> Dict[str, int]:
        """Get warmup requirements from all indicators."""
        return self.indicator_manager.get_warmup_requirements()
    
    def warmup_indicators(self, historical_data: list) -> None:
        """Warm up all indicators with historical data."""
        self.log.info(f"Warming up indicators with {len(historical_data)} bars")
        
        for bar in historical_data:
            self.indicator_manager.update_all(bar)
        
        self.warmup_complete = True
        self.log.info("Indicator warmup complete")
    
    def on_bar(self, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process new bar data - matches V1 behavior exactly."""
        # Update indicators
        self.indicator_manager.update_all(bar)
        
        # Generate signals if warmup is complete
        if not self.warmup_complete:
            return None
            
        indicator_values = self.indicator_manager.get_current_values()
        signals = self.signal_manager.generate_signals(indicator_values, bar)
        
        # Get combined signal
        combined_signal = self.signal_manager.get_combined_signal()
        
        # Extract bar data for processing
        bar_close = bar.get('close', 0.0)
        bar_open = bar.get('open', bar_close)
        bar_high = bar.get('high', bar_close)
        bar_low = bar.get('low', bar_close)
        
        # Debug logging like V1
        self.log.debug(
            "Bar received: O=%.2f H=%.2f L=%.2f C=%.2f, signal=%s",
            bar_open, bar_high, bar_low, bar_close,
            combined_signal.signal_type.value if combined_signal else None
        )
        
        # Update last seen price for graceful exit
        self._last_price = bar_close
        
        # Check exit conditions first (like V1)
        if self.position is not None:
            # 1) Stop-loss hit
            if self.position == "LONG" and bar_close <= (self._stop_price or 0):
                self._record_trade(bar_close, bar.get('timestamp'), reason="SL_HIT")
                return None
            elif self.position == "SHORT" and bar_close >= (self._stop_price or 0):
                self._record_trade(bar_close, bar.get('timestamp'), reason="SL_HIT")
                return None
            
            # 2) Trend reversal - opposite signal
            elif (combined_signal and 
                  combined_signal.signal_type in [SignalType.LONG, SignalType.SHORT] and
                  combined_signal.signal_type.value != self.position):
                self._record_trade(bar_close, bar.get('timestamp'), reason="REVERSAL")
                # After closing, enter new trade per fresh signal
                self._enter_position(combined_signal, bar)
                return self._format_signal_response(combined_signal)
        
        # Entry conditions (like V1)
        if (self.position is None and 
            combined_signal and 
            combined_signal.signal_type in [SignalType.LONG, SignalType.SHORT]):
            
            self.log.info(
                "Signal: direction=%s entry=%.2f stop=%.2f",
                combined_signal.signal_type.value,
                combined_signal.metadata.get('entry_price', bar_close),
                combined_signal.metadata.get('stop_price', bar_close)
            )
            
            self._enter_position(combined_signal, bar)
            return self._format_signal_response(combined_signal)
        
        # Log no signal reasons (like V1)
        if combined_signal is None or combined_signal.signal_type == SignalType.NO_SIGNAL:
            if combined_signal and combined_signal.reasons:
                self.log.debug("No signal reason(s): %s", " | ".join(combined_signal.reasons))
        
        return None
    
    def on_quote(self, quote: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process quote data - not used in this strategy."""
        return None
    
    def enable_indicator(self, indicator_name: str) -> bool:
        """Enable a specific indicator."""
        return self.indicator_manager.enable_indicator(indicator_name)
    
    def disable_indicator(self, indicator_name: str) -> bool:
        """Disable a specific indicator."""
        return self.indicator_manager.disable_indicator(indicator_name)
    
    def enable_signal_generator(self, generator_name: str) -> bool:
        """Enable a specific signal generator."""
        return self.signal_manager.enable_signal_generator(generator_name)
    
    def disable_signal_generator(self, generator_name: str) -> bool:
        """Disable a specific signal generator."""
        return self.signal_manager.disable_signal_generator(generator_name)
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart configuration for visualization."""
        chart_config = {
            'indicators': self.indicator_manager.get_chart_configs(),
            'signals': self.signal_manager.get_chart_configs()
        }
        
        return chart_config
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy status."""
        return {
            'strategy_name': self.__class__.__name__,
            'warmup_complete': self.warmup_complete,
            'position': self.position,
            'last_signal': self.last_signal.to_dict() if self.last_signal else None,
            'indicators': self.indicator_manager.get_indicator_status(),
            'signal_generators': self.signal_manager.get_status()
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration for persistence."""
        # Convert dataclass to dict using asdict
        from dataclasses import asdict
        return {
            'strategy_config': asdict(self.config),
            'indicators_config': self.indicator_manager.get_indicator_status(),
            'signals_config': self.signal_manager.get_status()
        }
    
    def reset(self) -> None:
        """Reset strategy state."""
        self.position = None
        self.last_signal = None
        self.warmup_complete = False
        
        # Reset all indicators
        self.indicator_manager.reset_all()
        self.signal_manager.reset_all()
        
        self.log.info("Strategy reset complete")
    
    def get_current_indicator_values(self) -> Dict[str, Any]:
        """Get current values of all indicators.
        
        Returns:
            Dictionary mapping indicator names to their current values
        """
        current_values = self.indicator_manager.get_current_values()
        
        # Convert to simple dictionary for logging/display
        result = {}
        for name, indicator_value in current_values.items():
            if indicator_value:
                if len(indicator_value.values) == 1:
                    result[name] = indicator_value.get_main_value()
                else:
                    result[name] = indicator_value.values
            else:
                result[name] = None
        
        return result
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy status.
        
        Returns:
            Dictionary containing strategy status information
        """
        return {
            "strategy_name": self.__class__.__name__,
            "initialized": self.warmup_complete,
            "config": {
                "risk_per_trade": self.config.risk_per_trade,
                "timeframe": self.config.timeframe,
                "historical_warmup": self.config.historical_warmup
            },
            "indicators": self.indicator_manager.get_indicator_status(),
            "signals": self.signal_manager.get_status(),
            "last_signal": {
                "type": self.last_signal.signal_type.value if self.last_signal else None,
                "confidence": self.last_signal.confidence if self.last_signal else None,
                "timestamp": self.last_signal.timestamp.isoformat() if self.last_signal else None,
                "reasons": self.last_signal.reasons if self.last_signal else []
            },
            "warmup_requirements": self.get_warmup_requirements()
        }
    
    def toggle_indicator_visibility(self, indicator_name: str) -> bool:
        """Toggle chart visibility for an indicator.
        
        Args:
            indicator_name: Name of the indicator
            
        Returns:
            True if successful, False otherwise
        """
        return self.indicator_manager.toggle_chart_visibility(indicator_name)
    
    def export_configurations(self, export_dir: str) -> None:
        """Export current configurations to files.
        
        Args:
            export_dir: Directory to save configuration files
        """
        import os
        os.makedirs(export_dir, exist_ok=True)
        
        # Export indicator config
        indicator_config_path = os.path.join(export_dir, "indicators.yaml")
        self.indicator_manager.export_config(indicator_config_path)
        
        # Export signal config
        signal_config_path = os.path.join(export_dir, "signals.yaml")
        self.signal_manager.export_config(signal_config_path)
        
        # Export strategy config
        strategy_config_path = os.path.join(export_dir, "strategy.yaml")
        self.config.to_yaml(strategy_config_path)
        
        self.logger.info(f"Exported configurations to: {export_dir}")
    
    def is_ready(self) -> bool:
        """Check if strategy is ready for trading.
        
        Returns:
            True if strategy is ready, False otherwise
        """
        return (self.warmup_complete and 
                self.indicator_manager.are_all_ready() and
                self.signal_manager.has_enabled_generators())
    
    def _enter_position(self, signal: 'TradingSignal', bar: Dict[str, Any]) -> None:
        """Enter a new position based on signal."""
        from utils.signals.base import SignalType
        
        direction = signal.signal_type.value
        entry_price = signal.metadata.get('entry_price', bar.get('close', 0.0))
        stop_price = signal.metadata.get('stop_price', bar.get('close', 0.0))
        
        # Update internal state
        self.position = direction
        self._entry_price = float(entry_price)
        self._stop_price = float(stop_price)
        self._entry_ts = bar.get('timestamp')
        self._entry_oi = bar.get('oi')
        
        self.log.info(
            "New %s position @ %.2f (SL %.2f)",
            direction, entry_price, stop_price
        )
    
    def _record_trade(self, exit_price: float, ts: Any, reason: str) -> None:
        """Record a completed trade (matches V1 format)."""
        if self._entry_price is None or self.position is None:
            return

        def _ts_to_date(val: Any) -> str:
            try:
                if hasattr(val, 'strftime'):
                    return val.strftime("%Y-%m-%d")
                # Handle other timestamp formats
                from datetime import datetime
                return datetime.utcnow().strftime("%Y-%m-%d")
            except Exception:
                from datetime import datetime
                return datetime.utcnow().strftime("%Y-%m-%d")

        exit_price = float(exit_price)
        realised = (
            exit_price - self._entry_price
            if self.position == "LONG"
            else self._entry_price - exit_price
        )
        pct = (realised / self._entry_price * 100) if self._entry_price else 0.0
        
        trade = {
            "Instrument": "UNKNOWN",  # filled by runner
            "Entry_Date": _ts_to_date(self._entry_ts),
            "Trade_Type": "Long" if self.position == "LONG" else "Short",
            "Exit_Reason": reason,
            "Entry_Price": round(self._entry_price, 2),
            "IV": None,
            "OI": getattr(self, "_entry_oi", None),
            "Exit_Date": _ts_to_date(ts) if ts != "END" else _ts_to_date(self._entry_ts),
            "Exit_Price": round(exit_price, 2),
            "Threshold": None,
            "SL_Price": round(self._stop_price or 0.0, 2),
            "Realised_PnL": round(realised, 2),
            "PnL%": round(pct, 2),
            "MDD_pct": None,
            "Sharpe": None,
            "Cum_PnL": None,
        }
        
        self.trades.append(trade)
        
        # Reset position
        self.position = None
        self._entry_price = None
        self._stop_price = None
        
        self.log.info(f"Trade closed: {reason} - P&L: {realised:.2f} ({pct:.2f}%)")
    
    def _format_signal_response(self, signal: 'TradingSignal') -> Dict[str, Any]:
        """Format signal response for runner compatibility."""
        return {
            'direction': signal.signal_type.value,
            'entry_price': signal.metadata.get('entry_price', signal.price),
            'stop_price': signal.metadata.get('stop_price', signal.price),
            'confidence': signal.confidence,
            'reasons': signal.reasons,
            'metadata': signal.metadata
        }
    
    def on_stop(self) -> None:
        """Handle strategy stop (matches V1 behavior)."""
        self.log.info("Strategy stopped. Closing position if any.")
        if self.position is not None and self._entry_price is not None:
            price = getattr(self, "_last_price", self._entry_price)
            self._record_trade(price, ts="END", reason="END")
        self.position = None 