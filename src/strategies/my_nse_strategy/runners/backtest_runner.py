#!/usr/bin/env python3
"""
MyNSEStrategy Backtest Runner

This module provides a strategy-specific backtest runner that uses the generic
backtest utilities from src/backtest_utils.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, BacktestRunConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.examples.strategies.ema_cross import EMACross
from nautilus_trader.examples.strategies.ema_cross import EMACrossConfig
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

from src.backtest_utils.config_loader import BacktestConfigLoader
from src.backtest_utils.data_loader import DataLoader
from src.backtest_utils.engine_launcher import BacktestEngineLauncher
from src.backtest_utils.results_aggregator import ResultsAggregator
from src.strategies.my_nse_strategy.strategy import MyNSEStrategy
from src.strategies.my_nse_strategy.config import MyNSEStrategyConfig


class MyNSEBacktestRunner:
    """
    Strategy-specific backtest runner for MyNSEStrategy.
    
    This class extends the generic backtest utilities with strategy-specific
    configuration and logic.
    """
    
    def __init__(self, config_path: str = "config/backtest_config.json"):
        """
        Initialize the backtest runner.
        
        Args:
            config_path: Path to the backtest configuration file
        """
        self.config_loader = BacktestConfigLoader(config_path)
        self.data_loader = DataLoader()
        self.engine_launcher = BacktestEngineLauncher()
        self.results_aggregator = ResultsAggregator()
        
        # Strategy-specific configuration
        self.strategy_config = MyNSEStrategyConfig(
            instrument_id="NIFTY-INDEX.NSE",
            position_size=1,
            sl_pct=0.02,
            tp_pct=0.03,
            lookback_intervals=2,
            entry_buffer_pct=0.01,
            min_iv=0.0,
            min_oi_change=-100,
            breakeven_trigger_pct=2.0,
            sar_enabled=True,
        )
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backtest.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def run_single_instrument_backtest(
        self,
        instrument_id: str,
        start_date: str,
        end_date: str,
        output_dir: str = "backtest_results"
    ) -> Dict:
        """
        Run backtest for a single instrument.
        
        Args:
            instrument_id: The instrument ID to backtest
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_dir: Directory to save results
            
        Returns:
            Dictionary containing backtest results
        """
        self.logger.info(f"Starting single instrument backtest for {instrument_id}")
        
        # Load configuration
        config = self.config_loader.load_config()
        
        # Update strategy config for this instrument
        strategy_config = MyNSEStrategyConfig(
            instrument_id=instrument_id,
            position_size=1,
            sl_pct=0.02,
            tp_pct=0.03,
            lookback_intervals=2,
            entry_buffer_pct=0.01,
            min_iv=0.0,
            min_oi_change=-100,
            breakeven_trigger_pct=2.0,
            sar_enabled=True,
        )
        
        # Load data
        data = self.data_loader.load_instrument_data(
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=end_date,
            catalog_path=config.get("catalog_path", "catalog-data")
        )
        
        if not data:
            self.logger.error(f"No data found for instrument {instrument_id}")
            return {}
            
        # Create engine config
        engine_config = BacktestEngineConfig(
            logging=LoggingConfig(
                log_level="INFO",
                log_file_path=f"{output_dir}/backtest_{instrument_id}_{datetime.now().strftime('%H-%M-%S')}.log"
            ),
            risk_engine=RiskEngineConfig(
                bypass=True,
                max_order_submit_rate="100/00:00:01",
                max_order_modify_rate="100/00:00:01",
                max_notional_per_order=1_000_000,
            ),
        )
        
        # Launch backtest
        results = self.engine_launcher.run_backtest(
            engine_config=engine_config,
            run_config=BacktestRunConfig(
                start_time=datetime.fromisoformat(f"{start_date}T09:15:00"),
                end_time=datetime.fromisoformat(f"{end_date}T15:30:00"),
                venues=[Venue("NSE")],
            ),
            data=data,
            strategy_configs=[strategy_config],
            output_dir=output_dir
        )
        
        self.logger.info(f"Single instrument backtest completed for {instrument_id}")
        return results
        
    def run_batch_backtest(
        self,
        instruments: List[str],
        start_date: str,
        end_date: str,
        output_dir: str = "backtest_results"
    ) -> Dict:
        """
        Run backtest for multiple instruments.
        
        Args:
            instruments: List of instrument IDs to backtest
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_dir: Directory to save results
            
        Returns:
            Dictionary containing aggregated backtest results
        """
        self.logger.info(f"Starting batch backtest for {len(instruments)} instruments")
        
        # Load configuration
        config = self.config_loader.load_config()
        
        # Load data for all instruments
        all_data = {}
        for instrument_id in instruments:
            data = self.data_loader.load_instrument_data(
                instrument_id=instrument_id,
                start_date=start_date,
                end_date=end_date,
                catalog_path=config.get("catalog_path", "catalog-data")
            )
            if data:
                all_data[instrument_id] = data
            else:
                self.logger.warning(f"No data found for instrument {instrument_id}")
                
        if not all_data:
            self.logger.error("No data found for any instruments")
            return {}
            
        # Create strategy configs for all instruments
        strategy_configs = []
        for instrument_id in all_data.keys():
            strategy_config = MyNSEStrategyConfig(
                instrument_id=instrument_id,
                position_size=1,
                sl_pct=0.02,
                tp_pct=0.03,
                lookback_intervals=2,
                entry_buffer_pct=0.01,
                min_iv=0.0,
                min_oi_change=-100,
                breakeven_trigger_pct=2.0,
                sar_enabled=True,
            )
            strategy_configs.append(strategy_config)
            
        # Create engine config
        engine_config = BacktestEngineConfig(
            logging=LoggingConfig(
                log_level="INFO",
                log_file_path=f"{output_dir}/batch_backtest_{datetime.now().strftime('%H-%M-%S')}.log"
            ),
            risk_engine=RiskEngineConfig(
                bypass=True,
                max_order_submit_rate="100/00:00:01",
                max_order_modify_rate="100/00:00:01",
                max_notional_per_order=1_000_000,
            ),
        )
        
        # Launch batch backtest
        results = self.engine_launcher.run_backtest(
            engine_config=engine_config,
            run_config=BacktestRunConfig(
                start_time=datetime.fromisoformat(f"{start_date}T09:15:00"),
                end_time=datetime.fromisoformat(f"{end_date}T15:30:00"),
                venues=[Venue("NSE")],
            ),
            data=all_data,
            strategy_configs=strategy_configs,
            output_dir=output_dir
        )
        
        # Aggregate results
        aggregated_results = self.results_aggregator.aggregate_results(results)
        
        self.logger.info(f"Batch backtest completed for {len(instruments)} instruments")
        return aggregated_results


def main():
    """Main function to run backtests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MyNSEStrategy backtests")
    parser.add_argument("--mode", choices=["single", "batch"], required=True,
                       help="Backtest mode: single instrument or batch")
    parser.add_argument("--instrument", type=str,
                       help="Instrument ID for single mode")
    parser.add_argument("--instruments", nargs="+",
                       help="List of instrument IDs for batch mode")
    parser.add_argument("--start-date", type=str, required=True,
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, required=True,
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", type=str, default="backtest_results",
                       help="Output directory for results")
    parser.add_argument("--config", type=str, default="config/backtest_config.json",
                       help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize runner
    runner = MyNSEBacktestRunner(args.config)
    
    if args.mode == "single":
        if not args.instrument:
            print("Error: --instrument is required for single mode")
            return
            
        results = runner.run_single_instrument_backtest(
            instrument_id=args.instrument,
            start_date=args.start_date,
            end_date=args.end_date,
            output_dir=args.output_dir
        )
        
    elif args.mode == "batch":
        if not args.instruments:
            print("Error: --instruments is required for batch mode")
            return
            
        results = runner.run_batch_backtest(
            instruments=args.instruments,
            start_date=args.start_date,
            end_date=args.end_date,
            output_dir=args.output_dir
        )
        
    print(f"Backtest completed. Results saved to {args.output_dir}")


if __name__ == "__main__":
    main() 