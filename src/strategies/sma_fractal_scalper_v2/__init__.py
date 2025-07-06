"""SMA Fractal Scalper V2 - Pluggable Architecture Implementation.

This strategy demonstrates the new pluggable indicator and signal generation
architecture. It separates:
- Indicator calculations (SMA, Fractal) into pluggable components
- Signal generation logic into a separate module
- Strategy execution logic focused on position management

This allows for:
- Easy testing of individual components
- Configuration-driven indicator management
- Chart visualization of indicators and signals
- Reusable components across strategies
"""

from .strategy import SmaFractalScalperV2
from .config import SmaFractalScalperV2Config

__all__ = [
    "SmaFractalScalperV2",
    "SmaFractalScalperV2Config",
] 