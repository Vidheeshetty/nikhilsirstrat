#!/usr/bin/env python3
"""
Paper Trading Runner

Main script to run paper trading with multiple strategies and brokers.
Provides real-time monitoring, reporting, and risk management.
"""

import asyncio
import argparse
import logging
import signal
import sys
from datetime import datetime, time
from pathlib import Path
import yaml
from typing import Dict, Any

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[2]
for p in (ROOT_DIR, ROOT_DIR / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from src.brokers.manager import BrokerManager
from src.brokers.base import OrderStatus
from utils.reporting.paper_trading_reporter import PaperTradingReporter
from utils.runners.paper_trading_runner import PaperTradingStrategyRunner

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Main paper trading engine that orchestrates strategies, brokers, and reporting.
    """

    def __init__(self, config_file: str):
        """Initialize paper trading engine."""
        self.config_file = config_file
        self.config = self._load_config()

        # Core components
        self.broker_manager = BrokerManager()
        self.reporter = PaperTradingReporter(self.config.get("reporting", {}))
        self.strategy_runners: Dict[str, PaperTradingStrategyRunner] = {}

        # State management
        self.running = False
        self.start_time = None

        # Setup logging
        self._setup_logging()

        logger.info("Paper trading engine initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config file {self.config_file}: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get("logging", {})

        # Create logs directory
        log_file = log_config.get("file", "runlogs/papertrading/paper_trading.log")
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_config.get("level", "INFO")),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )

    async def initialize(self):
        """Initialize all components."""
        try:
            # Initialize broker manager
            await self.broker_manager.initialize(self.config_file)

            # Initialize reporter
            await self.reporter.initialize()

            # Initialize strategy runners
            strategies_config = self.config.get("strategies", {})
            for strategy_name, strategy_config in strategies_config.items():
                if strategy_config.get("enabled", True):
                    await self._initialize_strategy(strategy_name, strategy_config)

            logger.info("Paper trading engine initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize paper trading engine: {e}")
            raise

    async def _initialize_strategy(self, name: str, config: Dict[str, Any]):
        """Initialize a strategy runner. Supports custom runner classes via
        the *runner* field inside the strategy config block. Falls back to the
        generic ``PaperTradingStrategyRunner`` stub if not specified."""
        try:
            broker_name = config.get("broker", "zerodha")
            config_file = config.get("config_file")

            # ------------------------------------------------------------------
            # Dynamically resolve runner class if fully-qualified path given
            # ------------------------------------------------------------------
            runner_cls = PaperTradingStrategyRunner
            runner_fqcn = config.get("runner")  # Fully qualified class name
            if runner_fqcn:
                try:
                    module_path, class_name = runner_fqcn.rsplit(".", 1)
                    import importlib  # local import keeps top of file clean

                    module = importlib.import_module(module_path)
                    runner_cls = getattr(module, class_name)
                except Exception as exc:  # pragma: no cover
                    logger.warning(
                        "Unable to import runner '%s' for strategy %s – falling back to default. (%s)",
                        runner_fqcn,
                        name,
                        exc,
                    )

            # Instantiate runner ------------------------------------------------
            runner = runner_cls(
                strategy_name=name,
                broker_manager=self.broker_manager,
                broker_name=broker_name,
                config_file=config_file,
                instrument_id=config.get("instrument_id"),
            )

            await runner.initialize()
            self.strategy_runners[name] = runner

            logger.info(f"Initialized strategy runner: {name}")

        except Exception as e:
            logger.error(f"Failed to initialize strategy {name}: {e}")
            raise

    async def start(self):
        """Start paper trading engine."""
        if self.running:
            logger.warning("Paper trading engine is already running")
            return

        try:
            self.running = True
            self.start_time = datetime.now()

            logger.info("Starting paper trading engine...")

            # Start all strategy runners
            for name, runner in self.strategy_runners.items():
                await runner.start()
                logger.info(f"Started strategy: {name}")

            # Start reporter
            await self.reporter.start()

            # Start main loop
            await self._main_loop()

        except Exception as e:
            logger.error(f"Error starting paper trading engine: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop paper trading engine."""
        if not self.running:
            return

        logger.info("Stopping paper trading engine...")

        self.running = False

        # Stop all strategy runners
        for name, runner in self.strategy_runners.items():
            try:
                await runner.stop()
                logger.info(f"Stopped strategy: {name}")
            except Exception as e:
                logger.error(f"Error stopping strategy {name}: {e}")

        # Stop reporter
        try:
            await self.reporter.stop()
        except Exception as e:
            logger.error(f"Error stopping reporter: {e}")

        # Shutdown broker manager
        try:
            await self.broker_manager.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down broker manager: {e}")

        logger.info("Paper trading engine stopped")

    async def _main_loop(self):
        """Main execution loop."""
        logger.info("Paper trading engine started successfully")

        # Market hours check
        market_config = self.config.get("data_feed", {})
        market_start = time.fromisoformat(
            market_config.get("market_start_time", "09:15")
        )
        market_end = time.fromisoformat(market_config.get("market_end_time", "15:30"))

        try:
            while self.running:
                current_time = datetime.now().time()

                # Check if within market hours
                if market_start <= current_time <= market_end:
                    # Update market data and process strategies
                    await self._process_market_update()

                    # Update reporting
                    await self._update_reporting()

                    # Check risk limits
                    await self._check_risk_limits()

                # Sleep for update frequency
                update_freq = self.config.get("data_feed", {}).get(
                    "update_frequency", 1
                )
                await asyncio.sleep(update_freq)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise

    async def _process_market_update(self):
        """Process market data updates."""
        try:
            # Get market data from brokers
            for runner in self.strategy_runners.values():
                await runner.process_market_update()

        except Exception as e:
            logger.error(f"Error processing market update: {e}")

    async def _update_reporting(self):
        """Update reporting data."""
        try:
            # Collect data from all components
            broker_data = await self.broker_manager.get_account_balance()
            positions = await self.broker_manager.get_positions()
            orders = await self.broker_manager.get_orders()

            # Update reporter
            await self.reporter.update(
                broker_data=broker_data,
                positions=positions,
                orders=orders,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error updating reporting: {e}")

    async def _check_risk_limits(self):
        """Check global risk limits."""
        try:
            risk_config = self.config.get("risk_management", {})

            # Get current account status
            balances = await self.broker_manager.get_account_balance()

            for broker_name, balance in balances.items():
                if isinstance(balance, dict) and "total_balance" in balance:
                    total_balance = balance["total_balance"]
                    unrealized_pnl = balance.get("unrealized_pnl", 0)

                    # Check daily loss limit
                    max_daily_loss = risk_config.get("global_max_daily_loss", 100000)
                    if unrealized_pnl < -max_daily_loss:
                        logger.warning(
                            f"Daily loss limit exceeded for {broker_name}: {unrealized_pnl}"
                        )
                        await self._emergency_stop(
                            f"Daily loss limit exceeded: {unrealized_pnl}"
                        )
                        return

                    # Check drawdown limit
                    max_drawdown = risk_config.get("max_drawdown_limit", 0.15)
                    initial_balance = getattr(
                        self.broker_manager.get_broker(broker_name),
                        "_initial_balance",
                        1000000,
                    )
                    current_drawdown = (
                        initial_balance - total_balance
                    ) / initial_balance

                    if current_drawdown > max_drawdown:
                        logger.warning(
                            f"Drawdown limit exceeded for {broker_name}: {current_drawdown:.2%}"
                        )
                        await self._emergency_stop(
                            f"Drawdown limit exceeded: {current_drawdown:.2%}"
                        )
                        return

        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")

    async def _emergency_stop(self, reason: str):
        """Emergency stop all trading."""
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")

        # Stop all strategy runners
        for runner in self.strategy_runners.values():
            await runner.emergency_stop()

        # Cancel all open orders
        orders = await self.broker_manager.get_orders()
        for order in orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.OPEN]:
                await self.broker_manager.cancel_order(order.order_id)

        # Close all positions (if configured)
        # This would be implemented based on risk management requirements

        await self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime": str(datetime.now() - self.start_time)
            if self.start_time
            else None,
            "strategies": {
                name: runner.get_status()
                for name, runner in self.strategy_runners.items()
            },
            "broker_stats": self.broker_manager.get_statistics(),
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Paper Trading Engine")
    parser.add_argument(
        "--config", default="config/paper_trading.yaml", help="Configuration file path"
    )
    parser.add_argument("--strategy", help="Specific strategy to run (optional)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (no actual orders)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Create engine
    engine = PaperTradingEngine(args.config)

    # After engine logging configured, widen level if --verbose passed
    if args.verbose:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        for h in root.handlers:
            h.setLevel(logging.DEBUG)

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(engine.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize and start engine
        await engine.initialize()

        if args.strategy:
            # Run specific strategy only
            if args.strategy not in engine.strategy_runners:
                logger.error(f"Strategy {args.strategy} not found")
                return 1

            # Disable other strategies
            for name, runner in engine.strategy_runners.items():
                if name != args.strategy:
                    runner.enabled = False

        # Start the engine
        await engine.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error running paper trading engine: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
