from __future__ import annotations

"""BacktestOrchestrator for the trend_riding_strategy.

This trimmed-down orchestrator is only intended to prove that the new folder
structure builds and imports correctly. It wires together the shared helpers
from utils.runner with the local ConfigManager, DataManager and Strategy.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.runner.engine_manager import EngineManager
from utils.runner.results_processor import ResultsProcessor
from utils.runner.report_generator import ReportGenerator

from strategies.trend_riding_strategy.config import TrendRidingStrategyConfig
from strategies.trend_riding_strategy.strategy import TrendRidingStrategy
from .config_manager import ConfigManager
from .data_manager import DataManager


class BacktestOrchestrator:
    """Coordinate all components for a single strategy back-test."""

    def __init__(
        self,
        config_file: str,
        catalog_path: str | None = None,
        base_dir: str = "_summary.txts",
    ) -> None:
        self.config_manager = ConfigManager(config_file)
        self.data_manager = DataManager(catalog_path)
        self.engine_manager = EngineManager()
        self.results_processor = ResultsProcessor()
        self.report_generator = ReportGenerator(base_dir)

        self.config_manager.validate_config()

    # ------------------------------------------------------------------
    def run_single_backtest(
        self,
        instrument_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        verbose: bool = True,
        log_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a single-instrument back-test. This stub skips real data feed."""

        if verbose:
            print(f"[INFO] Backtesting {instrument_id} (stub mode)")

        strategy_cfg = self.config_manager.get_strategy_config(instrument_id)
        strategy = TrendRidingStrategy(config=strategy_cfg)

        # Create engine
        engine = self.engine_manager.create_engine(verbose=verbose)
        self.engine_manager.setup_venue(engine)

        # Add dummy instrument and empty data
        instrument = self.data_manager.get_instrument(instrument_id)
        self.engine_manager.add_instrument(engine, instrument)
        self.engine_manager.add_data(
            engine,
            self.data_manager.get_quote_ticks(instrument_id, start_time, end_time),
        )

        # Add strategy
        self.engine_manager.add_strategy(engine, strategy)

        # Run (will immediately finish because no data)
        self.engine_manager.run_backtest(engine)
        result = self.engine_manager.get_results(engine)

        detailed = self.results_processor.extract_detailed_data(
            engine, result, log_file or "stub.log"
        )
        summary = self.results_processor.create_summary_data(
            result, detailed, instrument_id
        )

        # Optionally write summary
        if log_file is not None:
            self.report_generator.write_summary_only(summary, filename=log_file)

        self.engine_manager.cleanup()
        return summary
