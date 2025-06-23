#!/usr/bin/env python3
"""
Backtest Orchestrator for MyNSEStrategy

Main orchestrator that coordinates all components and manages the backtest workflow.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import concurrent.futures

from .config_manager import ConfigManager
from .data_manager import DataManager
from .engine_manager import EngineManager
from .results_processor import ResultsProcessor
from ..report_generator import ReportGenerator
from strategies.my_nse_strategy.strategy import MyNSEStrategy
from .batch_helpers import run_single_backtest_wrapper_for_pool


class BacktestOrchestrator:
    """Main orchestrator for backtest execution."""
    
    def __init__(self, 
                 config_file: str,
                 catalog_path: str = "catalog-data/my_nse_strategy/catalog",
                 base_dir: str = "/Users/nitindhawan/Downloads/Code Repository/NTbasedPlatform/_summary.txts"):
        self.config_manager = ConfigManager(config_file)
        self.data_manager = DataManager(catalog_path)
        self.engine_manager = EngineManager()
        self.results_processor = ResultsProcessor()
        self.report_generator = ReportGenerator(base_dir)
        
        # Validate configuration
        self.config_manager.validate_config()
    
    def run_single_backtest(self, 
                           instrument_id: str,
                           start_time: Optional[str] = None,
                           end_time: Optional[str] = None,
                           log_file: Optional[str] = None,
                           verbose: bool = True,
                           batch_mode: bool = False) -> Dict[str, Any]:
        """Run backtest for a single instrument."""
        
        # Setup logging only if log_file is not None
        if log_file is None:
            do_logging = False
        else:
            do_logging = True
            base_dir = Path(self.report_generator.base_dir) / datetime.now().strftime("%Y-%m-%d")
            base_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%H-%M-%S")
            if not log_file:
                log_file = str(base_dir / f"{timestamp}-backtest-{instrument_id.replace('/', '_')}.log")
        
        # Always print detailed info for single runs if verbose
        if verbose:
            print(f"Running backtest for instrument: {instrument_id}")
        
        try:
            # Get configuration
            strategy_config = self.config_manager.get_strategy_config(instrument_id)
            backtest_params = self.config_manager.get_backtest_params(start_time, end_time)
            
            # Validate data availability
            if not self.data_manager.validate_instrument_data(
                instrument_id, backtest_params["start_time"], backtest_params["end_time"]
            ):
                raise ValueError(f"No data available for instrument {instrument_id}")
            
            # Setup engine
            engine = self.engine_manager.create_engine(verbose=verbose)
            self.engine_manager.setup_venue(engine)
            
            # Add instrument and data
            instrument = self.data_manager.get_instrument(instrument_id)
            self.engine_manager.add_instrument(engine, instrument)
            
            data = self.data_manager.get_quote_ticks(
                instrument_id, backtest_params["start_time"], backtest_params["end_time"]
            )
            self.engine_manager.add_data(engine, data)
            
            # Add strategy
            strategy = MyNSEStrategy(config=strategy_config)
            self.engine_manager.add_strategy(engine, strategy)
            
            # Run backtest
            self.engine_manager.run_backtest(engine)
            result = self.engine_manager.get_results(engine)
            
            # Process results
            detailed_data = self.results_processor.extract_detailed_data(engine, result, log_file if log_file else "tmp.log")
            summary = self.results_processor.create_summary_data(result, detailed_data, instrument_id, batch_mode=batch_mode)
            # For batch runs, include stats_pnls and account_data in the returned dict
            if batch_mode:
                # Try to serialize stats_pnls (if present)
                stats_pnls = getattr(result, 'stats_pnls', None)
                if stats_pnls:
                    try:
                        # Convert any non-serializable values to float
                        serializable_stats = {}
                        for k, v in stats_pnls.items():
                            serializable_stats[k] = {}
                            for subk, subv in v.items():
                                try:
                                    serializable_stats[k][subk] = float(subv)
                                except Exception:
                                    serializable_stats[k][subk] = str(subv)
                        summary['stats_pnls'] = serializable_stats
                    except Exception:
                        summary['stats_pnls'] = str(stats_pnls)
                # Also include account_data
                summary['account'] = detailed_data.get('account', {})
            
            # Only log if requested
            if do_logging:
                # Write BACKTEST RESULTS SUMMARY (summary only) first, then ORDER DATA, POSITION DATA, TRADE DATA
                self.report_generator.write_summary_only(log_file, summary)
                self.report_generator.print_order_data(detailed_data, log_file)
                self.report_generator.print_position_data(detailed_data, log_file)
                self.report_generator.print_trade_data(detailed_data, log_file)
            
            # Cleanup
            self.engine_manager.cleanup()
            
            if verbose:
                print(f"Backtest completed for {instrument_id}. Results saved to: {log_file if log_file else '[no log file]'}")
            return summary
            
        except Exception as e:
            print(f"Error running backtest for {instrument_id}: {e}")
            self.engine_manager.cleanup()
            raise
    
    def run_batch_backtest(self, 
                          instrument_ids: List[str],
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          verbose: bool = False,
                          max_workers: int = 10) -> List[Dict[str, Any]]:
        """Run backtest for multiple instruments, logging to a single file."""
        
        all_results = []
        base_dir = Path(self.report_generator.base_dir) / datetime.now().strftime("%Y-%m-%d")
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H-%M-%S")
        batch_log_file = str(base_dir / f"{timestamp}-batch-backtest.log")
        if verbose:
            print(f"Starting batch backtest for {len(instrument_ids)} instruments")
        with open(batch_log_file, "w") as batch_log:
            batch_log.write("=" * 100 + "\n")
            batch_log.write(f"BATCH BACKTEST REPORT\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            batch_log.write(f"Total Instruments: {len(instrument_ids)}\n")
            batch_log.write("=" * 100 + "\n\n")
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            total = len(instrument_ids)
            for i, instrument_id in enumerate(instrument_ids, 1):
                if verbose:
                    print(f"\n{'='*40}\nRunning backtest {i}/{total}: {instrument_id}\n{'='*40}")
                else:
                    msg = f"Processing {i}/{total}"
                    print('\r' + msg.ljust(40), end='', flush=True)
                futures.append(executor.submit(
                    run_single_backtest_wrapper_for_pool,
                    self.config_manager.config_file,
                    self.data_manager.catalog_path,
                    self.report_generator.base_dir,
                    instrument_id,
                    start_time,
                    end_time,
                    verbose,
                    batch_mode=True
                ))

            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                if "error" in result:
                    if verbose:
                        print(f"Failed to run backtest for {result['instrument_id']}: {result['error']}")
                else:
                    all_results.append(result)
                if not verbose:
                    msg = f"Processing {i}/{total}"
                    print('\r' + msg.ljust(40), end='', flush=True)
            if not verbose:
                print('\r' + ' ' * 40, end='\r')  # Clear the line
                print()  # Move to next line after progress bar
        
        # After all_results is populated, write the report in the correct order
        if all_results:
            # 1. Write the detailed BACKTEST RESULTS SUMMARY (totals/aggregates) at the top
            self.report_generator.write_batch_results_summary(batch_log_file, all_results)

            # 2. Write the instrument-wise summary table after the detailed summary
            with open(batch_log_file, "a") as batch_log:
                batch_log.write("INSTRUMENT-WISE SUMMARY\n")
                batch_log.write("-" * 100 + "\n")
                batch_log.write(f"{'Instrument':<40} | {'Orders':>8} | {'Positions':>10} | {'Trades':>8} | {'Realized PnL':>14} | {'Unrealized PnL':>16}\n")
                batch_log.write("-" * 100 + "\n")
                for result in all_results:
                    instrument_id_short = result['instrument_id'][:37] + '...' if len(result['instrument_id']) > 40 else result['instrument_id']
                    realized_pnl = float(result.get('realized_pnl', 0.0))
                    unrealized_pnl = float(result.get('unrealized_pnl', 0.0))
                    batch_log.write(
                        f"{instrument_id_short:<40} | {result['total_orders']:>8} | {result['total_positions']:>10} | {result['total_trades']:>8} | {realized_pnl:>14,.2f} | {unrealized_pnl:>16,.2f}\n"
                    )
                batch_log.write("-" * 100 + "\n\n")
        
        return all_results
    
    def run_all_instruments_backtest(self,
                                   start_time: Optional[str] = None,
                                   end_time: Optional[str] = None,
                                   verbose: bool = False,
                                   max_workers: int = 10) -> List[Dict[str, Any]]:
        """Run backtest for all available instruments."""
        instrument_ids = self.data_manager.get_all_instrument_ids()
        if verbose:
            print(f"Found {len(instrument_ids)} instruments for backtesting")
        return self.run_batch_backtest(instrument_ids, start_time, end_time, verbose=verbose, max_workers=max_workers) 