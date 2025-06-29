#!/usr/bin/env python3
"""
Modular Backtest Runner for MyNSEStrategy

This module provides a clean, modular interface for running backtests using the
new component-based architecture.

Usage:
    # Run with default config
    python modular_backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE"

    # Override specific parameters
    python modular_backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --start_time "2025-06-18T12:00:00"

    # Use custom config file
    python modular_backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --config_file "custom_config.yaml"

    # Run for all instruments
    python modular_backtest_runner.py --instrument_id "all"
"""

import argparse
import logging
import sys
import os
from pathlib import Path
import datetime


# Set logging level based on --verbose flag (default WARNING)
def configure_logging(verbose):
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


# Parse arguments early to set logging before other imports
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--verbose", action="store_true", default=False)
args, _ = parser.parse_known_args()
configure_logging(args.verbose)

# Dynamically search for 'src' directory upwards and add to sys.path
current = Path(__file__).resolve()
for _ in range(10):
    if (current / "src").is_dir():
        src_path = current / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        break
    current = current.parent

import argparse
from typing import Optional

from strategies.my_nse_strategy.runners.backtest.backtest_orchestrator import (
    BacktestOrchestrator,
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Modular Backtest Runner for MyNSEStrategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single instrument backtest
  python modular_backtest_runner.py --instrument_id "NIFTY.OPT.03Jul2025.22800.CALL.NSE"
  
  # Override time range
  python modular_backtest_runner.py --instrument_id "NIFTY.OPT.03Jul2025.22800.CALL.NSE" \\
                                    --start_time "2025-06-18T15:00:00" \\
                                    --end_time "2025-06-20T10:00:00"
  
  # All instruments backtest
  python modular_backtest_runner.py --instrument_id "all"
  
  # Custom config file
  python modular_backtest_runner.py --instrument_id "NIFTY.OPT.03Jul2025.22800.CALL.NSE" \\
                                    --config_file "custom_strategy.yaml"
        """,
    )

    parser.add_argument(
        "--instrument_id",
        type=str,
        required=False,
        default=None,
        help="Instrument ID to backtest, or 'all' for all instruments. If not provided, uses YAML config.",
    )

    parser.add_argument(
        "--config_file",
        type=str,
        default="src/strategies/my_nse_strategy/config/strategy.yaml",
        help="Path to the strategy configuration file",
    )

    parser.add_argument(
        "--catalog_path",
        type=str,
        default="catalog-data/my_nse_strategy/catalog",
        help="Path to the data catalog",
    )

    parser.add_argument(
        "--start_time",
        type=str,
        default=None,
        help="Backtest start time in ISO format (e.g., '2025-06-18T15:00:00'). Overrides config.",
    )

    parser.add_argument(
        "--end_time",
        type=str,
        default=None,
        help="Backtest end time in ISO format (e.g., '2025-06-20T10:00:00'). Overrides config.",
    )

    parser.add_argument(
        "--base_dir",
        type=str,
        default="_summary.txts",
        help="Base directory for output files",
    )

    parser.add_argument(
        "--log_file",
        type=str,
        default=None,
        help="Specific log file path (optional, auto-generated if not provided)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output (prints detailed info for each instrument)",
    )

    parser.add_argument(
        "--max_workers",
        type=int,
        default=10,
        help="Number of concurrent backtests to run in parallel (default: 10)",
    )

    return parser.parse_args()


def validate_arguments(args):
    """Validate command line arguments."""
    # Check if config file exists
    if not Path(args.config_file).exists():
        raise FileNotFoundError(f"Configuration file not found: {args.config_file}")

    # Check if catalog path exists
    if not Path(args.catalog_path).exists():
        raise FileNotFoundError(f"Catalog path not found: {args.catalog_path}")

    # Validate time format if provided
    if args.start_time:
        try:
            datetime.datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(
                f"Invalid start_time format: {args.start_time}. Use ISO format (e.g., '2025-06-18T15:00:00')"
            )

    if args.end_time:
        try:
            datetime.datetime.fromisoformat(args.end_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(
                f"Invalid end_time format: {args.end_time}. Use ISO format (e.g., '2025-06-20T10:00:00')"
            )


def run_single_instrument_backtest(
    orchestrator: BacktestOrchestrator,
    instrument_id: str,
    start_time: Optional[str],
    end_time: Optional[str],
    log_file: Optional[str],
    verbose: bool,
    base_dir: str,
):
    """Run backtest for a single instrument."""
    # Use instrument_id from YAML if not provided
    if instrument_id is None:
        instrument_id = orchestrator.config_manager.config.get("instrument_id")
    # Auto-generate log file if not specified
    if log_file is None:
        # Use instrument_id or 'unknown' if None
        instrument_id_str = instrument_id or "unknown"
        timestamp = datetime.datetime.now().strftime("%H-%M-%S")
        log_dir = Path(base_dir) / datetime.datetime.now().strftime("%Y-%m-%d")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(
            log_dir / f"{timestamp}-backtest-{instrument_id_str.replace('/', '_')}.log"
        )
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting Single Instrument Backtest")
        print(f"{'=' * 60}")
        print(f"Instrument: {instrument_id}")
        print(f"Start Time: {start_time or 'From Config'}")
        print(f"End Time: {end_time or 'From Config'}")
        print(f"{'=' * 60}\n")
    try:
        result = orchestrator.run_single_backtest(
            instrument_id=instrument_id,
            start_time=start_time,
            end_time=end_time,
            log_file=log_file,
            verbose=verbose,
        )
        if verbose:
            print(f"\n✅ Backtest completed successfully!")
            print(f"📊 Results Summary:")
            print(f"   - Total Orders: {result['total_orders']}")
            print(f"   - Total Trades: {result['total_trades']}")
            print(f"   - Total PnL: {result['pnl_total']} {result['currency']}")
            print(f"   - PnL %: {result['pnl_pct_total']}%")
            print(f"   - Log file: {log_file}")
        return result
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        raise


def run_all_instruments_backtest(
    orchestrator: BacktestOrchestrator,
    start_time: Optional[str],
    end_time: Optional[str],
    verbose: bool,
    max_workers: int,
):
    """Run backtest for all available instruments."""
    # Only print progress (instrument X/Y) unless verbose is set
    try:
        results = orchestrator.run_all_instruments_backtest(
            start_time=start_time,
            end_time=end_time,
            verbose=verbose,
            max_workers=max_workers,
        )
        print(f"\n✅ Batch backtest completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Instruments tested: {len(results)}")
        print(
            f"   - Total orders across all instruments: {sum(r['total_orders'] for r in results)}"
        )
        print(
            f"   - Total trades across all instruments: {sum(r['total_trades'] for r in results)}"
        )
        return results
    except Exception as e:
        print(f"❌ Batch backtest failed: {e}")
        raise


def main():
    """Main entry point for the modular backtest runner."""
    try:
        # Parse and validate arguments
        args = parse_arguments()
        validate_arguments(args)

        print("🔧 Initializing Modular Backtest Runner...")

        # Create orchestrator
        orchestrator = BacktestOrchestrator(
            config_file=args.config_file,
            catalog_path=args.catalog_path,
            base_dir=args.base_dir,
        )

        print("✅ Orchestrator initialized successfully!")

        # Run appropriate backtest based on instrument_id
        if args.instrument_id is None:
            # Use instrument from YAML config
            print("No instrument_id provided. Using instrument from YAML config.")
            result = run_single_instrument_backtest(
                orchestrator=orchestrator,
                instrument_id=None,
                start_time=args.start_time,
                end_time=args.end_time,
                log_file=args.log_file,
                verbose=True,  # Always verbose for single run
                base_dir=args.base_dir,
            )
        elif args.instrument_id.lower() == "all":
            results = run_all_instruments_backtest(
                orchestrator=orchestrator,
                start_time=args.start_time,
                end_time=args.end_time,
                verbose=args.verbose,
                max_workers=args.max_workers,
            )
        else:
            result = run_single_instrument_backtest(
                orchestrator=orchestrator,
                instrument_id=args.instrument_id,
                start_time=args.start_time,
                end_time=args.end_time,
                log_file=args.log_file,
                verbose=True,  # Always verbose for single run
                base_dir=args.base_dir,
            )

        print(f"\n🎉 Backtest execution completed successfully!")
        print(f"📁 Check the '{args.base_dir}' directory for detailed reports.")

    except KeyboardInterrupt:
        print("\n⚠️  Backtest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Backtest failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
