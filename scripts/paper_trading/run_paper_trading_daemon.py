#!/usr/bin/env python3
"""
Paper Trading Daemon

Runs paper trading as a background daemon service with proper logging,
monitoring, and remote management capabilities.
"""

import asyncio
import argparse
import logging
import logging.handlers
import signal
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import yaml
import psutil
from typing import Dict, Any
import queue

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.brokers.manager import BrokerManager
from src.brokers.base import OrderStatus
from utils.reporting.paper_trading_reporter import PaperTradingReporter
from utils.runners.paper_trading_runner import PaperTradingStrategyRunner


class PaperTradingDaemon:
    """
    Paper trading daemon that runs in the background.

    Features:
    - Background execution
    - Process monitoring
    - Remote control via files/API
    - Health checks
    - Automatic restart on failure
    - Resource monitoring
    """

    def __init__(self, config_file: str, daemon_mode: bool = True):
        """Initialize paper trading daemon."""
        self.config_file = config_file
        self.daemon_mode = daemon_mode
        self.config = self._load_config()

        # Daemon state
        self.running = False
        self.start_time = None
        self.pid_file = Path("runlogs/papertrading/daemon.pid")
        self.status_file = Path("runlogs/papertrading/daemon_status.json")
        self.control_file = Path("runlogs/papertrading/daemon_control.json")

        # Core components
        self.broker_manager = BrokerManager()
        self.reporter = PaperTradingReporter(self.config.get("reporting", {}))
        self.strategy_runners: Dict[str, PaperTradingStrategyRunner] = {}

        # Monitoring
        self.health_stats = {}
        self.error_count = 0
        self.last_heartbeat = None

        # Control queue for commands
        self.command_queue = queue.Queue()

        # Setup daemon logging
        self._setup_daemon_logging()

        self.logger = logging.getLogger(__name__)
        self.logger.info("Paper trading daemon initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config file {self.config_file}: {e}")
            sys.exit(1)

    def _setup_daemon_logging(self):
        """Setup logging for daemon mode."""
        log_config = self.config.get("logging", {})

        # Create logs directory
        log_file = Path(log_config.get("file", "runlogs/papertrading/daemon.log"))
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure logging for daemon mode
        if self.daemon_mode:
            # Daemon mode: only file logging
            logging.basicConfig(
                level=getattr(logging, log_config.get("level", "INFO")),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(log_file),
                    logging.handlers.RotatingFileHandler(
                        log_file,
                        maxBytes=10 * 1024 * 1024,  # 10MB
                        backupCount=5,
                    ),
                ],
            )
        else:
            # Interactive mode: both file and console
            logging.basicConfig(
                level=getattr(logging, log_config.get("level", "INFO")),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout),
                ],
            )

    def daemonize(self):
        """Daemonize the process."""
        if not self.daemon_mode:
            return

        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit parent
        except OSError as e:
            self.logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit second parent
        except OSError as e:
            self.logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        with open("/dev/null", "r") as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open("/dev/null", "w") as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
        with open("/dev/null", "w") as f:
            os.dup2(f.fileno(), sys.stderr.fileno())

        # Write PID file
        self._write_pid_file()

    def _write_pid_file(self):
        """Write process ID to file."""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

    def _remove_pid_file(self):
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def _update_status(self, status: str, extra_info: Dict[str, Any] = None):
        """Update daemon status file."""
        try:
            # Format uptime with milliseconds to 2 decimal places
            uptime_formatted = None
            if self.start_time:
                uptime_delta = datetime.now() - self.start_time
                total_seconds = uptime_delta.total_seconds()
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                milliseconds = (seconds % 1) * 1000
                uptime_formatted = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:.2f}"
            
            status_data = {
                "status": status,
                "pid": os.getpid(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "last_update": datetime.now().isoformat(),
                "uptime": uptime_formatted,
                "error_count": self.error_count,
                "health_stats": self.health_stats,
                **(extra_info or {}),
            }

            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.status_file, "w") as f:
                json.dump(status_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error updating status file: {e}")

    def _check_control_commands(self):
        """Check for control commands."""
        try:
            if self.control_file.exists():
                with open(self.control_file, "r") as f:
                    command_data = json.load(f)

                command = command_data.get("command")
                if command:
                    self.command_queue.put(command_data)

                    # Clear control file
                    self.control_file.unlink()

        except Exception as e:
            self.logger.error(f"Error checking control commands: {e}")

    def _process_commands(self):
        """Process queued commands."""
        while not self.command_queue.empty():
            try:
                command_data = self.command_queue.get_nowait()
                command = command_data.get("command")

                if command == "stop":
                    self.logger.info("Received stop command")
                    self.running = False
                elif command == "restart":
                    self.logger.info("Received restart command")
                    # This will be handled by the main loop
                    pass
                elif command == "status":
                    self.logger.info("Received status command")
                    self._update_status("running", {"requested_status": True})
                elif command == "health_check":
                    self.logger.info("Received health check command")
                    asyncio.create_task(self._perform_health_check())
                else:
                    self.logger.warning(f"Unknown command: {command}")

            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")

    async def _perform_health_check(self):
        """Perform comprehensive health check."""
        try:
            health_data = {}

            # System resources
            process = psutil.Process()
            health_data["cpu_percent"] = process.cpu_percent()
            health_data["memory_percent"] = process.memory_percent()
            health_data["memory_mb"] = process.memory_info().rss / 1024 / 1024

            # Broker health
            broker_health = await self.broker_manager.get_health_status()
            health_data["brokers"] = broker_health

            # Strategy health
            strategy_health = {}
            for name, runner in self.strategy_runners.items():
                strategy_health[name] = runner.get_status()
            health_data["strategies"] = strategy_health

            # Update health stats
            self.health_stats = health_data
            self.last_heartbeat = datetime.now()

            self.logger.info(f"Health check completed: {health_data}")

        except Exception as e:
            self.logger.error(f"Error in health check: {e}")
            self.error_count += 1

    async def initialize(self):
        """Initialize all components."""
        try:
            self.logger.info("Initializing paper trading daemon...")
            
            # Check if we have an event loop
            try:
                loop = asyncio.get_running_loop()
                self.logger.info(f"Event loop is running: {loop}")
            except RuntimeError as e:
                self.logger.error(f"No event loop running during initialization: {e}")
                raise

            # Initialize broker manager
            await self.broker_manager.initialize(self.config_file)

            # Initialize reporter
            await self.reporter.initialize()

            # Initialize strategy runners
            strategies_config = self.config.get("strategies", {})
            for strategy_name, strategy_config in strategies_config.items():
                if strategy_config.get("enabled", True):
                    await self._initialize_strategy(strategy_name, strategy_config)

            self.logger.info("Paper trading daemon initialization complete")

        except Exception as e:
            self.logger.error(f"Failed to initialize paper trading daemon: {e}")
            raise

    async def _initialize_strategy(self, name: str, config: Dict[str, Any]):
        """Initialize a strategy runner using the unified PaperTradingStrategyRunner interface."""
        try:
            broker_name = config.get("broker", "zerodha")
            config_file = config.get("config_file")
            instrument_id = config.get("instrument_id")

            # Use unified PaperTradingStrategyRunner - it handles all the dynamic loading
            runner = PaperTradingStrategyRunner(
                strategy_name=name,
                broker_manager=self.broker_manager,
                broker_name=broker_name,
                config_file=config_file,
                instrument_id=instrument_id,
            )

            await runner.initialize()
            self.strategy_runners[name] = runner

            self.logger.info(f"Initialized strategy runner: {name} via unified interface")

        except Exception as e:
            self.logger.error(f"Failed to initialize strategy {name}: {e}")
            raise

    async def start(self):
        """Start the daemon."""
        if self.running:
            self.logger.warning("Daemon is already running")
            return

        try:
            self.running = True
            self.start_time = datetime.now()

            # Write PID file (needed for status checking)
            self._write_pid_file()

            self.logger.info("Starting paper trading daemon...")
            self._update_status("starting")

            # Start all strategy runners
            for name, runner in self.strategy_runners.items():
                await runner.start()
                self.logger.info(f"Started strategy: {name}")

            # Start reporter
            await self.reporter.start()

            self._update_status("running")

            # Start main daemon loop
            await self._daemon_loop()

        except Exception as e:
            self.logger.error(f"Error starting daemon: {e}")
            self._update_status("error", {"error": str(e)})
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the daemon."""
        if not self.running:
            return

        self.logger.info("Stopping paper trading daemon...")
        self._update_status("stopping")

        self.running = False

        # Stop all strategy runners
        for name, runner in self.strategy_runners.items():
            try:
                await runner.stop()
                self.logger.info(f"Stopped strategy: {name}")
            except Exception as e:
                self.logger.error(f"Error stopping strategy {name}: {e}")

        # Stop reporter
        try:
            await self.reporter.stop()
        except Exception as e:
            self.logger.error(f"Error stopping reporter: {e}")

        # Shutdown broker manager
        try:
            await self.broker_manager.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down broker manager: {e}")

        self._update_status("stopped")
        self._remove_pid_file()

        self.logger.info("Paper trading daemon stopped")

    async def _daemon_loop(self):
        """Main daemon execution loop."""
        self.logger.info("Paper trading daemon started successfully")

        # Market hours check
        market_config = self.config.get("data_feed", {})
        market_start = market_config.get("market_start_time", "09:15")
        market_end = market_config.get("market_end_time", "15:30")

        # Health check interval
        health_check_interval = 60  # seconds
        last_health_check = datetime.now()

        try:
            while self.running:
                current_time = datetime.now()

                # Process control commands
                self._check_control_commands()
                self._process_commands()

                # Periodic health check
                if (current_time - last_health_check).seconds >= health_check_interval:
                    await self._perform_health_check()
                    last_health_check = current_time

                # Check if within market hours
                current_time_str = current_time.strftime("%H:%M")
                if market_start <= current_time_str <= market_end:
                    # Active trading hours
                    await self._process_market_update()
                    await self._update_reporting()
                    await self._check_risk_limits()

                    # Update status more frequently during market hours
                    self._update_status("running_active")
                    sleep_time = 1
                else:
                    # Outside market hours - less frequent updates
                    self._update_status("running_idle")
                    sleep_time = 10

                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            self.logger.info("Daemon loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in daemon loop: {e}")
            self.error_count += 1
            self._update_status("error", {"error": str(e)})
            raise

    async def _process_market_update(self):
        """Process market data updates."""
        try:
            for runner in self.strategy_runners.values():
                await runner.process_market_update()
        except Exception as e:
            self.logger.error(f"Error processing market update: {e}")
            self.error_count += 1

    async def _update_reporting(self):
        """Update reporting data."""
        try:
            broker_data = await self.broker_manager.get_account_balance()
            positions = await self.broker_manager.get_positions()
            orders = await self.broker_manager.get_orders()

            await self.reporter.update(
                broker_data=broker_data,
                positions=positions,
                orders=orders,
                timestamp=datetime.now(),
            )
        except Exception as e:
            self.logger.error(f"Error updating reporting: {e}")
            self.error_count += 1

    async def _check_risk_limits(self):
        """Check global risk limits."""
        try:
            risk_config = self.config.get("risk_management", {})
            balances = await self.broker_manager.get_account_balance()

            for broker_name, balance in balances.items():
                if isinstance(balance, dict) and "total_balance" in balance:
                    total_balance = balance["total_balance"]
                    unrealized_pnl = balance.get("unrealized_pnl", 0)

                    # Check daily loss limit
                    max_daily_loss = risk_config.get("global_max_daily_loss", 100000)
                    if unrealized_pnl < -max_daily_loss:
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
                        await self._emergency_stop(
                            f"Drawdown limit exceeded: {current_drawdown:.2%}"
                        )
                        return

        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
            self.error_count += 1

    async def _emergency_stop(self, reason: str):
        """Emergency stop all trading."""
        self.logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        self._update_status("emergency_stop", {"reason": reason})

        # Stop all strategy runners
        for runner in self.strategy_runners.values():
            await runner.emergency_stop()

        # Cancel all open orders
        orders = await self.broker_manager.get_orders()
        for order in orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.OPEN]:
                await self.broker_manager.cancel_order(order.order_id)

        await self.stop()


def is_daemon_running(pid_file: Path) -> bool:
    """Check if daemon is already running."""
    if not pid_file.exists():
        return False

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Check if process is still running
        return psutil.pid_exists(pid)
    except (ValueError, FileNotFoundError):
        return False


def send_daemon_command(command: str, control_file: Path):
    """Send command to running daemon."""
    command_data = {
        "command": command,
        "timestamp": datetime.now().isoformat(),
        "sender": "cli",
    }

    control_file.parent.mkdir(parents=True, exist_ok=True)
    with open(control_file, "w") as f:
        json.dump(command_data, f, indent=2)

    print(f"Command '{command}' sent to daemon")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Paper Trading Daemon")
    parser.add_argument(
        "--config", default="config/paper_trading.yaml", help="Configuration file path"
    )
    parser.add_argument(
        "--daemon", action="store_true", help="Run as daemon (background process)"
    )
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Get daemon status")
    parser.add_argument("--restart", action="store_true", help="Restart daemon")

    args = parser.parse_args()

    pid_file = Path("runlogs/papertrading/daemon.pid")
    status_file = Path("runlogs/papertrading/daemon_status.json")
    control_file = Path("runlogs/papertrading/daemon_control.json")

    # Handle daemon control commands
    if args.stop:
        if is_daemon_running(pid_file):
            send_daemon_command("stop", control_file)
        else:
            print("Daemon is not running")
        return 0

    if args.status:
        if is_daemon_running(pid_file):
            if status_file.exists():
                with open(status_file, "r") as f:
                    status_data = json.load(f)
                print("Daemon Status:")
                print(json.dumps(status_data, indent=2))
            else:
                print("Daemon is running but status file not found")
        else:
            print("Daemon is not running")
        return 0

    if args.restart:
        if is_daemon_running(pid_file):
            send_daemon_command("stop", control_file)
            time.sleep(2)  # Wait for stop
        # Fall through to start daemon

    # Check if already running
    if is_daemon_running(pid_file) and not args.restart:
        print("Daemon is already running")
        return 1

    # Create and start daemon
    daemon = PaperTradingDaemon(args.config, daemon_mode=args.daemon)

    # Setup signal handlers
    def signal_handler(signum, frame):
        daemon.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(daemon.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Daemonize if requested
        if args.daemon:
            daemon.logger.info("Running in daemon mode - daemonizing...")
            daemon.daemonize()
        else:
            daemon.logger.info("Running in foreground mode")

        # Initialize and start daemon
        daemon.logger.info("About to initialize daemon...")
        await daemon.initialize()
        daemon.logger.info("About to start daemon...")
        await daemon.start()

    except KeyboardInterrupt:
        daemon.logger.info("Interrupted by user")
    except Exception as e:
        daemon.logger.error(f"Error running daemon: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
