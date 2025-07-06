"""Paper trading strategy runner module.

Provides the main unified CLI interface for executing any strategy in paper trading mode.
This runner acts as a factory that dynamically loads the appropriate strategy-specific runner.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

__all__ = ["PaperTradingStrategyRunner"]


class PaperTradingStrategyRunner:
    """
    Unified CLI interface for paper trading strategies.

    This class acts as a factory that:
    1. Accepts strategy configuration via CLI parameters
    2. Dynamically loads the appropriate strategy-specific runner
    3. Delegates all operations to the loaded runner
    4. Provides a consistent interface regardless of strategy type
    """

    def __init__(
        self,
        strategy_name: str,
        broker_manager: Any,
        broker_name: str,
        config_file: str | None = None,
        instrument_id: str | None = None,
        **kwargs: Any,
    ):
        """Initialize the unified paper trading runner.

        Args:
            strategy_name: Name of the strategy to run
            broker_manager: Broker manager instance
            broker_name: Name of the broker to use
            config_file: Path to strategy config file
            instrument_id: Instrument to trade
            **kwargs: Additional parameters passed to strategy runner
        """
        self.strategy_name = strategy_name
        self.broker_manager = broker_manager
        self.broker_name = broker_name
        self.config_file = config_file
        self.instrument_id = instrument_id
        self.kwargs = kwargs

        # The actual strategy runner instance (loaded dynamically)
        self._strategy_runner: Optional[Any] = None
        self._strategy_config: Optional[Dict[str, Any]] = None

        logger.info(
            f"PaperTradingStrategyRunner initialized for strategy: {strategy_name}"
        )

    async def initialize(self):
        """Initialize by loading the appropriate strategy runner."""
        try:
            # Load strategy configuration to determine runner class
            self._strategy_config = self._load_strategy_config()

            # Determine runner class to use
            runner_class = self._resolve_runner_class()

            # Create strategy runner instance
            self._strategy_runner = runner_class(
                strategy_name=self.strategy_name,
                broker_manager=self.broker_manager,
                broker_name=self.broker_name,
                config_file=self.config_file,
                instrument_id=self.instrument_id,
                **self.kwargs,
            )

            # Initialize the strategy runner
            if hasattr(self._strategy_runner, "initialize"):
                await self._strategy_runner.initialize()

            logger.info(
                f"Successfully loaded and initialized runner: {runner_class.__name__}"
            )

        except Exception as e:
            logger.error(
                f"Failed to initialize strategy runner for {self.strategy_name}: {e}"
            )
            raise

    def _load_strategy_config(self) -> Dict[str, Any]:
        """Load strategy configuration from file."""
        if not self.config_file:
            logger.warning(f"No config file specified for {self.strategy_name}")
            return {}

        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                logger.warning(f"Config file not found: {self.config_file}")
                return {}

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded strategy config from {self.config_file}")
                return config

        except Exception as e:
            logger.error(f"Error loading strategy config from {self.config_file}: {e}")
            return {}

    def _resolve_runner_class(self) -> type:
        """Resolve the appropriate runner class for this strategy."""
        # Strategy-specific runner class mappings
        STRATEGY_RUNNERS = {
            "SmaFractalScalper": "src.strategies.sma_fractal_scalper.runner.papertrade_runner.sma_scalper_paper_runner.SmaFractalScalperPaperRunner",
            "SmaFractalScalperV2": "src.strategies.sma_fractal_scalper_v2.runner.papertrade_runner.sma_scalper_v2_paper_runner.SmaFractalScalperV2PaperRunner",
            "TrendRiding": "src.strategies.trend_riding.runner.paper_runner.TrendRidingPaperRunner",
            "SwingRangeExpansion": "src.strategies.swing_range_expansion.runner.paper_runner.SwingRangeExpansionPaperRunner",
        }

        # Try to get runner class from strategy config first
        if self._strategy_config and "runner" in self._strategy_config:
            runner_fqcn = self._strategy_config["runner"]
            logger.info(f"Using runner from config: {runner_fqcn}")
        # Fall back to predefined mappings
        elif self.strategy_name in STRATEGY_RUNNERS:
            runner_fqcn = STRATEGY_RUNNERS[self.strategy_name]
            logger.info(
                f"Using predefined runner for {self.strategy_name}: {runner_fqcn}"
            )
        else:
            raise ValueError(
                f"No runner class found for strategy: {self.strategy_name}"
            )

        # Dynamically import the runner class
        try:
            module_path, class_name = runner_fqcn.rsplit(".", 1)
            module = importlib.import_module(module_path)
            runner_class = getattr(module, class_name)

            logger.info(f"Successfully imported runner class: {runner_class.__name__}")
            return runner_class

        except Exception as e:
            logger.error(f"Failed to import runner class {runner_fqcn}: {e}")
            raise ImportError(f"Could not load runner class {runner_fqcn}: {e}")

    async def start(self):
        """Start the strategy runner."""
        if not self._strategy_runner:
            raise RuntimeError(
                "Strategy runner not initialized. Call initialize() first."
            )

        logger.info(
            f"Starting {self.strategy_name} via {self._strategy_runner.__class__.__name__}"
        )
        return await self._strategy_runner.start()

    async def stop(self):
        """Stop the strategy runner."""
        if not self._strategy_runner:
            return

        logger.info(f"Stopping {self.strategy_name}")
        return await self._strategy_runner.stop()

    async def process_market_update(self):
        """Process market updates via the strategy runner."""
        if not self._strategy_runner:
            return None

        if hasattr(self._strategy_runner, "process_market_update"):
            return await self._strategy_runner.process_market_update()
        return None

    async def emergency_stop(self):
        """Emergency stop via the strategy runner."""
        if not self._strategy_runner:
            return

        logger.warning(f"Emergency stop triggered for {self.strategy_name}")
        if hasattr(self._strategy_runner, "emergency_stop"):
            return await self._strategy_runner.emergency_stop()

    def get_status(self) -> Dict[str, Any]:
        """Get status from the strategy runner."""
        if not self._strategy_runner:
            return {
                "enabled": False,
                "positions": 0,
                "pnl": 0.0,
                "status": "not_initialized",
            }

        if hasattr(self._strategy_runner, "get_status"):
            status = self._strategy_runner.get_status()
            status["strategy_name"] = self.strategy_name
            status["runner_class"] = self._strategy_runner.__class__.__name__
            return status

        return {
            "enabled": True,
            "positions": 0,
            "pnl": 0.0,
            "strategy_name": self.strategy_name,
            "runner_class": self._strategy_runner.__class__.__name__,
            "status": "running",
        }

    def run(self) -> Any:
        """Execute the paper trading strategy."""
        if not self._strategy_runner:
            raise RuntimeError(
                "Strategy runner not initialized. Call initialize() first."
            )

        if hasattr(self._strategy_runner, "run"):
            return self._strategy_runner.run()

        logger.warning(
            f"Strategy runner {self._strategy_runner.__class__.__name__} does not implement run() method"
        )
        return None

    # Delegation methods for additional functionality
    def __getattr__(self, name: str) -> Any:
        """Delegate any other method calls to the underlying strategy runner."""
        if self._strategy_runner and hasattr(self._strategy_runner, name):
            return getattr(self._strategy_runner, name)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )
