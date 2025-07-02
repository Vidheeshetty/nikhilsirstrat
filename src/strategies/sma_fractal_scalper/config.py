from __future__ import annotations

from dataclasses import dataclass

from utils.strategy.base_strategy import StrategyConfigBase


@dataclass
class SmaFractalScalperConfig(StrategyConfigBase):
    """Configuration for SmaFractalScalper strategy."""

    sma_short_period: int = 5
    sma_long_period: int = 200
    risk_per_trade: float = 0.01  # fraction of account per trade (unused placeholder)
    timeframe: str = "1MIN"
    session_cutoff: str | None = None  # e.g. "15:25" – force flat before EOD
    use_fractals: bool = True  # toggle fractal breakout filter
    use_sma: bool = (
        True  # toggle SMA crossover filter (if False, pure fractal breakout)
    )
    fractal_window: int = (
        5  # total bars used for fractal detection (3=1 bar either side)
    )
    historical_warmup: bool = True  # load historical data for indicator warm-up
