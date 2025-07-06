"""Configuration for SMA Fractal Scalper V2 strategy.

This configuration demonstrates the pluggable architecture where indicators
and signals are configured separately from the strategy logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import yaml
from pathlib import Path


@dataclass
class SmaFractalScalperV2Config:
    """Configuration for SMA Fractal Scalper V2 strategy."""
    
    # Strategy parameters (compatible with original strategy)
    risk_per_trade: float = 0.01
    timeframe: str = '1MIN'
    session_cutoff: Optional[str] = None
    
    # End-of-day position management
    enable_eod_closing: bool = True
    eod_closing_time: str = "15:20"  # Time to close positions (HH:MM format)
    eod_buffer_minutes: int = 10  # Minutes before market close to stop taking new positions
    eod_order_type: str = "MARKET"  # Order type for EOD closing (MARKET/LIMIT)
    eod_limit_offset_pct: float = 0.1  # Offset percentage for limit orders (0.1% = 0.001)
    
    # Original strategy parameters for backward compatibility
    sma_short_period: int = 5
    sma_long_period: int = 200
    use_fractals: bool = True
    use_sma: bool = True
    fractal_window: int = 5
    
    # Indicator configuration file
    indicators_config_path: str = "src/strategies/sma_fractal_scalper_v2/indicators.yaml"
    
    # Signal configuration file
    signals_config_path: str = "src/strategies/sma_fractal_scalper_v2/signals.yaml"
    
    # Chart configuration
    chart_enabled: bool = True
    chart_config_path: str = "src/strategies/sma_fractal_scalper_v2/chart.yaml"
    
    # Historical warmup
    historical_warmup: bool = True
    
    # Additional parameters that might be in config files
    instrument_id: Optional[str] = None
    strategy_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    max_position_size: Optional[int] = None
    max_daily_trades: Optional[int] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    log_level: Optional[str] = None
    log_signals: Optional[bool] = None
    log_indicators: Optional[bool] = None
    
    # Catch-all for any additional parameters
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, **kwargs):
        """Initialize config with flexible parameter handling."""
        # Set known parameters
        known_params = {
            'risk_per_trade', 'timeframe', 'session_cutoff',
            'sma_short_period', 'sma_long_period', 'use_fractals', 'use_sma', 'fractal_window',
            'indicators_config_path', 'signals_config_path', 'chart_enabled', 'chart_config_path',
            'historical_warmup', 'instrument_id', 'strategy_name', 'description', 'version',
            'author', 'max_position_size', 'max_daily_trades', 'stop_loss_pct', 'take_profit_pct',
            'log_level', 'log_signals', 'log_indicators',
            'enable_eod_closing', 'eod_closing_time', 'eod_buffer_minutes', 'eod_order_type', 'eod_limit_offset_pct'
        }
        
        # Set defaults
        self.risk_per_trade = kwargs.get('risk_per_trade', 0.01)
        self.timeframe = kwargs.get('timeframe', '1MIN')
        self.session_cutoff = kwargs.get('session_cutoff', None)
        self.sma_short_period = kwargs.get('sma_short_period', 5)
        self.sma_long_period = kwargs.get('sma_long_period', 200)
        self.use_fractals = kwargs.get('use_fractals', True)
        self.use_sma = kwargs.get('use_sma', True)
        self.fractal_window = kwargs.get('fractal_window', 5)
        self.indicators_config_path = kwargs.get('indicators_config_path', 
                                                "src/strategies/sma_fractal_scalper_v2/indicators.yaml")
        self.signals_config_path = kwargs.get('signals_config_path', 
                                             "src/strategies/sma_fractal_scalper_v2/signals.yaml")
        self.chart_enabled = kwargs.get('chart_enabled', True)
        self.chart_config_path = kwargs.get('chart_config_path', 
                                           "src/strategies/sma_fractal_scalper_v2/chart.yaml")
        self.historical_warmup = kwargs.get('historical_warmup', True)
        self.instrument_id = kwargs.get('instrument_id', None)
        self.strategy_name = kwargs.get('strategy_name', None)
        self.description = kwargs.get('description', None)
        self.version = kwargs.get('version', None)
        self.author = kwargs.get('author', None)
        self.max_position_size = kwargs.get('max_position_size', None)
        self.max_daily_trades = kwargs.get('max_daily_trades', None)
        self.stop_loss_pct = kwargs.get('stop_loss_pct', None)
        self.take_profit_pct = kwargs.get('take_profit_pct', None)
        self.log_level = kwargs.get('log_level', None)
        self.log_signals = kwargs.get('log_signals', None)
        self.log_indicators = kwargs.get('log_indicators', None)
        self.enable_eod_closing = kwargs.get('enable_eod_closing', True)
        self.eod_closing_time = kwargs.get('eod_closing_time', "15:20")
        self.eod_buffer_minutes = kwargs.get('eod_buffer_minutes', 10)
        self.eod_order_type = kwargs.get('eod_order_type', "MARKET")
        self.eod_limit_offset_pct = kwargs.get('eod_limit_offset_pct', 0.1)
        
        # Store extra parameters
        self.extra_params = {k: v for k, v in kwargs.items() if k not in known_params}
        
        # Validate
        self._validate()
    
    def _validate(self):
        """Validate configuration after initialization."""
        if not 0.001 <= self.risk_per_trade <= 0.1:
            raise ValueError("Risk per trade must be between 0.1% and 10%")
        
        if self.timeframe not in ['1MIN', '5MIN', '15MIN', '1H', '1D']:
            raise ValueError("Timeframe must be one of: 1MIN, 5MIN, 15MIN, 1H, 1D")
        
        if not 1 <= self.sma_short_period <= 50:
            raise ValueError("SMA short period must be between 1 and 50")
        
        if not 50 <= self.sma_long_period <= 500:
            raise ValueError("SMA long period must be between 50 and 500")
        
        if self.sma_short_period >= self.sma_long_period:
            raise ValueError("SMA short period must be less than long period")
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'SmaFractalScalperV2Config':
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            SmaFractalScalperV2Config instance
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Handle both nested and flat configuration formats
        if 'strategy' in config_data:
            return cls(**config_data['strategy'])
        else:
            return cls(**config_data)
    
    def to_yaml(self, config_path: str) -> None:
        """Save configuration to YAML file.
        
        Args:
            config_path: Path to save YAML configuration file
        """
        config_data = {
            'strategy': {
                'risk_per_trade': self.risk_per_trade,
                'timeframe': self.timeframe,
                'session_cutoff': self.session_cutoff,
                'sma_short_period': self.sma_short_period,
                'sma_long_period': self.sma_long_period,
                'use_fractals': self.use_fractals,
                'use_sma': self.use_sma,
                'fractal_window': self.fractal_window,
                'indicators_config_path': self.indicators_config_path,
                'signals_config_path': self.signals_config_path,
                'chart_config_path': self.chart_config_path,
                'chart_enabled': self.chart_enabled,
                'historical_warmup': self.historical_warmup,
                'enable_eod_closing': self.enable_eod_closing,
                'eod_closing_time': self.eod_closing_time,
                'eod_buffer_minutes': self.eod_buffer_minutes,
                'eod_order_type': self.eod_order_type,
                'eod_limit_offset_pct': self.eod_limit_offset_pct,
                **self.extra_params
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
    
    def get_warmup_requirements(self) -> Dict[str, Any]:
        """Get warmup requirements for the strategy.
        
        Returns:
            Dictionary containing warmup information
        """
        # This will be dynamically calculated based on loaded indicators
        return {
            "historical_warmup": self.historical_warmup,
            "indicators_config": self.indicators_config_path,
            "signals_config": self.signals_config_path,
            "sma_long_period": self.sma_long_period,
            "fractal_window": self.fractal_window
        }