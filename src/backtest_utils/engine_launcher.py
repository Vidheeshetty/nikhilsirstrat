"""
Generic Engine Launcher for Backtesting

This module provides a generic engine launcher for backtesting strategies.
It handles creating and running backtest engines with Nautilus Trader.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, BacktestRunConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.model.identifiers import Venue


class BacktestEngineLauncher:
    """Generic engine launcher for backtesting."""

    def __init__(self):
        """Initialize the engine launcher."""
        pass

    def run_backtest(
        self,
        engine_config: BacktestEngineConfig,
        run_config: BacktestRunConfig,
        data: Dict[str, Any],
        strategy_configs: List[Any],
        output_dir: str = "backtest_results",
    ) -> Dict[str, Any]:
        """
        Run a backtest with the given configuration and data.

        Args:
            engine_config: Backtest engine configuration
            run_config: Backtest run configuration
            data: Dictionary containing instrument data
            strategy_configs: List of strategy configurations
            output_dir: Directory to save results

        Returns:
            Dictionary containing backtest results
        """
        try:
            # Create engine
            engine = BacktestEngine(config=engine_config)

            # Add venue
            engine.add_venue(
                venue=Venue("NSE"),
                oms_type="HEDGING",
                account_type="MARGIN",
                starting_balances=[],
                base_currency="INR",
            )

            # Add instruments and data
            if isinstance(data, dict) and "instrument" in data:
                # Single instrument data
                engine.add_instrument(data["instrument"])
                engine.add_data(data["ticks"])
            else:
                # Multiple instruments data
                for instrument_id, instrument_data in data.items():
                    if instrument_data and "instrument" in instrument_data:
                        engine.add_instrument(instrument_data["instrument"])
                        engine.add_data(instrument_data["ticks"])

            # Add strategies
            for strategy_config in strategy_configs:
                engine.add_strategy(strategy_config)

            # Run backtest
            engine.run()

            # Get results
            result = engine.get_result()

            # Save results
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%H-%M-%S")

            # Save summary
            summary_file = os.path.join(output_dir, f"backtest_summary_{timestamp}.txt")
            with open(summary_file, "w") as f:
                f.write("Backtest Results Summary\n")
                f.write("=======================\n")
                f.write(f"Start Time: {run_config.start_time}\n")
                f.write(f"End Time: {run_config.end_time}\n")
                f.write(f"Total Return: {result.total_return:.4f}\n")
                f.write(f"Sharpe Ratio: {result.sharpe_ratio:.4f}\n")
                f.write(f"Max Drawdown: {result.max_drawdown:.4f}\n")
                f.write(f"Total Trades: {result.total_trades}\n")
                f.write(f"Win Rate: {result.win_rate:.4f}\n")

            return {
                "result": result,
                "summary_file": summary_file,
                "output_dir": output_dir,
            }

        except Exception as e:
            print(f"Error running backtest: {e}")
            return {}

    def create_engine_config(
        self,
        log_level: str = "INFO",
        log_file_path: Optional[str] = None,
        bypass_risk_engine: bool = True,
    ) -> BacktestEngineConfig:
        """
        Create a backtest engine configuration.

        Args:
            log_level: Logging level
            log_file_path: Path to log file
            bypass_risk_engine: Whether to bypass risk engine

        Returns:
            BacktestEngineConfig object
        """
        return BacktestEngineConfig(
            logging=LoggingConfig(
                log_level=log_level,
                log_file_path=log_file_path,
            ),
            risk_engine=RiskEngineConfig(
                bypass=bypass_risk_engine,
                max_order_submit_rate="100/00:00:01",
                max_order_modify_rate="100/00:00:01",
                max_notional_per_order=1_000_000,
            ),
        )
