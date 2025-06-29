# Generic Batch Runner for Backtesting
# This is a refactored version of backtest_orchestrator.py, made generic for any strategy.

from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from pathlib import Path
import concurrent.futures

# These should be passed in or imported by the strategy-specific runner
# from .config_loader import ConfigManager
# from .data_loader import DataManager
# from .engine_launcher import EngineManager
# from .results_aggregator import ResultsProcessor
# from .batch_helpers import run_single_backtest_wrapper_for_pool


class BatchBacktestRunner:
    """Generic orchestrator for backtest execution."""

    def __init__(
        self,
        config_manager,
        data_manager,
        engine_manager,
        results_processor,
        report_generator=None,
    ):
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.engine_manager = engine_manager
        self.results_processor = results_processor
        self.report_generator = report_generator
        self.config_manager.validate_config()

    def run_single_backtest(
        self,
        instrument_id: str,
        strategy_class: Type,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        log_file: Optional[str] = None,
        verbose: bool = True,
        batch_mode: bool = False,
    ) -> Dict[str, Any]:
        """Run backtest for a single instrument."""
        do_logging = log_file is not None
        if do_logging:
            base_dir = Path(self.report_generator.base_dir) / datetime.now().strftime(
                "%Y-%m-%d"
            )
            base_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%H-%M-%S")
            if not log_file:
                log_file = str(
                    base_dir
                    / f"{timestamp}-backtest-{instrument_id.replace('/', '_')}.log"
                )
        if verbose:
            print(f"Running backtest for instrument: {instrument_id}")
        try:
            strategy_config = self.config_manager.get_strategy_config(instrument_id)
            backtest_params = self.config_manager.get_backtest_params(
                start_time, end_time
            )
            if not self.data_manager.validate_instrument_data(
                instrument_id,
                backtest_params["start_time"],
                backtest_params["end_time"],
            ):
                raise ValueError(f"No data available for instrument {instrument_id}")
            engine = self.engine_manager.create_engine(verbose=verbose)
            self.engine_manager.setup_venue(engine)
            instrument = self.data_manager.get_instrument(instrument_id)
            self.engine_manager.add_instrument(engine, instrument)
            data = self.data_manager.get_quote_ticks(
                instrument_id,
                backtest_params["start_time"],
                backtest_params["end_time"],
            )
            self.engine_manager.add_data(engine, data)
            strategy = strategy_class(config=strategy_config)
            self.engine_manager.add_strategy(engine, strategy)
            self.engine_manager.run_backtest(engine)
            result = self.engine_manager.get_results(engine)
            detailed_data = self.results_processor.extract_detailed_data(
                engine, result, log_file if log_file else "tmp.log"
            )
            summary = self.results_processor.create_summary_data(
                result, detailed_data, instrument_id, batch_mode=batch_mode
            )
            if batch_mode:
                stats_pnls = getattr(result, "stats_pnls", None)
                if stats_pnls:
                    try:
                        serializable_stats = {}
                        for k, v in stats_pnls.items():
                            serializable_stats[k] = {}
                            for subk, subv in v.items():
                                try:
                                    serializable_stats[k][subk] = float(subv)
                                except Exception:
                                    serializable_stats[k][subk] = str(subv)
                        summary["stats_pnls"] = serializable_stats
                    except Exception:
                        summary["stats_pnls"] = str(stats_pnls)
                summary["account"] = detailed_data.get("account", {})
            if do_logging and self.report_generator:
                self.report_generator.write_summary_only(log_file, summary)
                self.report_generator.print_order_data(detailed_data, log_file)
                self.report_generator.print_position_data(detailed_data, log_file)
                self.report_generator.print_trade_data(detailed_data, log_file)
            self.engine_manager.cleanup()
            if verbose:
                print(
                    f"Backtest completed for {instrument_id}. Results saved to: {log_file if log_file else '[no log file]'}"
                )
            return summary
        except Exception as e:
            print(f"Error running backtest for {instrument_id}: {e}")
            self.engine_manager.cleanup()
            raise

    def run_batch_backtest(
        self,
        instrument_ids: List[str],
        strategy_class: Type,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        verbose: bool = False,
        max_workers: int = 10,
    ) -> List[Dict[str, Any]]:
        """Run backtest for multiple instruments, logging to a single file."""
        all_results = []
        base_dir = Path(self.report_generator.base_dir) / datetime.now().strftime(
            "%Y-%m-%d"
        )
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H-%M-%S")
        batch_log_file = str(base_dir / f"{timestamp}-batch-backtest.log")
        if verbose:
            print(f"Starting batch backtest for {len(instrument_ids)} instruments")
        with open(batch_log_file, "w") as batch_log:
            batch_log.write("=" * 100 + "\n")
            batch_log.write(
                f"BATCH BACKTEST REPORT\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            batch_log.write(f"Total Instruments: {len(instrument_ids)}\n")
            batch_log.write("=" * 100 + "\n\n")
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            futures = []
            total = len(instrument_ids)
            for i, instrument_id in enumerate(instrument_ids, 1):
                if verbose:
                    print(
                        f"\n{'=' * 40}\nRunning backtest {i}/{total}: {instrument_id}\n{'=' * 40}"
                    )
                else:
                    msg = f"Processing {i}/{total}"
                    print("\r" + msg.ljust(40), end="", flush=True)
                futures.append(
                    executor.submit(
                        self.run_single_backtest,
                        instrument_id,
                        strategy_class,
                        start_time,
                        end_time,
                        None,
                        verbose,
                        True,
                    )
                )
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                if "error" in result:
                    if verbose:
                        print(
                            f"Failed to run backtest for {result['instrument_id']}: {result['error']}"
                        )
                else:
                    all_results.append(result)
                if not verbose:
                    msg = f"Processing {i}/{total}"
                    print("\r" + msg.ljust(40), end="", flush=True)
            if not verbose:
                print("\r" + " " * 40, end="\r")
                print()
        if all_results and self.report_generator:
            self.report_generator.write_batch_results_summary(
                batch_log_file, all_results
            )
            with open(batch_log_file, "a") as batch_log:
                batch_log.write("INSTRUMENT-WISE SUMMARY\n")
                batch_log.write("-" * 100 + "\n")
                batch_log.write(
                    f"{'Instrument':<40} | {'Orders':>8} | {'Positions':>10} | {'Trades':>8} | {'Realized PnL':>14} | {'Unrealized PnL':>16}\n"
                )
                batch_log.write("-" * 100 + "\n")
                for result in all_results:
                    instrument_id_short = (
                        result["instrument_id"][:37] + "..."
                        if len(result["instrument_id"]) > 40
                        else result["instrument_id"]
                    )
                    realized_pnl = float(result.get("realized_pnl", 0.0))
                    unrealized_pnl = float(result.get("unrealized_pnl", 0.0))
                    batch_log.write(
                        f"{instrument_id_short:<40} | {result['total_orders']:>8} | {result['total_positions']:>10} | {result['total_trades']:>8} | {realized_pnl:>14,.2f} | {unrealized_pnl:>16,.2f}\n"
                    )
                batch_log.write("-" * 100 + "\n\n")
        return all_results

    def run_all_instruments_backtest(
        self,
        strategy_class: Type,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        verbose: bool = False,
        max_workers: int = 10,
    ) -> List[Dict[str, Any]]:
        instrument_ids = self.data_manager.get_all_instrument_ids()
        if verbose:
            print(f"Found {len(instrument_ids)} instruments for backtesting")
        return self.run_batch_backtest(
            instrument_ids,
            strategy_class,
            start_time,
            end_time,
            verbose=verbose,
            max_workers=max_workers,
        )
