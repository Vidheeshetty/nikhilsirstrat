"""
Zerodha Configuration

Configuration class specific to Zerodha KiteConnect API.
Extends the base BrokerConfig with Zerodha-specific parameters.
"""

from dataclasses import dataclass
from typing import Dict
from ..base import BrokerConfig


@dataclass
class ZerodhaConfig(BrokerConfig):
    """Configuration for Zerodha KiteConnect API."""

    # Zerodha-specific settings
    app_name: str = "NTbasedPlatform"
    redirect_url: str = "https://127.0.0.1:8080"

    # KiteConnect API URLs
    base_url: str = "https://api.kite.trade"
    login_url: str = "https://kite.zerodha.com/connect/login"

    # Trading settings
    product_type: str = "MIS"  # MIS, CNC, NRML
    exchange: str = "NSE"

    # Paper trading settings (when paper_trading=True)
    paper_initial_balance: float = 1000000.0  # 10 Lakh
    paper_brokerage_per_order: float = 20.0  # Flat 20 per order
    paper_stt_rate: float = 0.025  # 0.025% STT on sell side
    paper_transaction_charges: float = 0.00325  # 0.00325% transaction charges

    # Rate limiting
    orders_per_second: int = 10
    quotes_per_second: int = 100

    # Instrument mapping
    instrument_file_url: str = "https://api.kite.trade/instruments"
    instrument_cache_ttl: int = 86400  # 24 hours

    # Market hours (IST)
    market_start_time: str = "09:15"
    market_end_time: str = "15:30"
    pre_market_start: str = "09:00"
    post_market_end: str = "15:45"

    # Risk management overrides
    max_position_size: int = 100  # Max contracts per position
    max_daily_loss: float = 50000.0  # Max daily loss in INR
    max_open_positions: int = 10  # Max open positions

    # Zerodha-specific instrument settings
    nse_equity_multiplier: int = 1
    nse_futures_multiplier: int = 1
    nse_options_multiplier: int = 1

    def __post_init__(self):
        """Post-initialization setup."""
        # Set broker name
        self.broker_name = "zerodha"

        # Validate required fields for live trading
        if not self.paper_trading:
            if not self.api_key:
                raise ValueError("api_key is required for live trading")
            if not self.api_secret:
                raise ValueError("api_secret is required for live trading")

    @classmethod
    def create_paper_config(cls, **kwargs) -> "ZerodhaConfig":
        """Create a paper trading configuration."""
        defaults = {
            "paper_trading": True,
            "api_key": "paper_key",
            "api_secret": "paper_secret",
            "log_level": "INFO",
        }
        defaults.update(kwargs)
        return cls(**defaults)

    @classmethod
    def create_live_config(
        cls, api_key: str, api_secret: str, access_token: str = "", **kwargs
    ) -> "ZerodhaConfig":
        """Create a live trading configuration."""
        defaults = {
            "paper_trading": False,
            "api_key": api_key,
            "api_secret": api_secret,
            "access_token": access_token,
            "log_level": "INFO",
        }
        defaults.update(kwargs)
        return cls(**defaults)

    def get_instrument_token_map(self) -> Dict[str, str]:
        """Get mapping of instrument symbols to tokens."""
        # This would be loaded from Zerodha's instrument file
        # For now, return common NSE instruments
        return {
            "NIFTY": "256265",
            "BANKNIFTY": "260105",
            "RELIANCE": "738561",
            "TCS": "2953217",
            "INFY": "408065",
        }

    def get_exchange_mapping(self) -> Dict[str, str]:
        """Get exchange mapping for different instrument types."""
        return {
            "equity": "NSE",
            "futures": "NFO",
            "options": "NFO",
            "currency": "CDS",
            "commodity": "MCX",
        }
