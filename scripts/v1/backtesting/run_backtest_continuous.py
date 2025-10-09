#!/usr/bin/env python3
"""Backtest runner for continuous futures contracts with date range filtering.

This script provides an easy interface to backtest strategies on continuous
futures data with optional date range filtering.

Examples:
---------
# Full data range
python scripts/v1/backtesting/run_backtest_continuous.py \\
    --strategy nd_tt_v4 \\
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE

# Specific date range
python scripts/v1/backtesting/run_backtest_continuous.py \\
    --strategy nd_tt_v4 \\
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \\
    --start_date 2024-01-01 \\
    --end_date 2024-12-31

# Custom catalog path
python scripts/v1/backtesting/run_backtest_continuous.py \\
    --strategy nd_tt_v4 \\
    --instrument_id NIFTY_CONTINUOUS.FUT.NSE \\
    --catalog_path catalog-data/nifty-continuous-yf/catalog \\
    --start_date 2024-06-01
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
for p in (ROOT_DIR, SRC_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from utils.reporting.controller import ReportController


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run backtest on continuous futures with date filtering"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="nd_tt_v4",
        help="Strategy folder name under src/strategies/",
    )
    parser.add_argument(
        "--instrument_id",
        type=str,
        required=True,
        help="Instrument ID (e.g., NIFTY_CONTINUOUS.FUT.NSE)",
    )
    parser.add_argument(
        "--catalog_path",
        type=str,
        default="catalog-data/nifty-continuous-yf/catalog",
        help="Path to Nautilus catalog",
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default=None,
        help="Start date for backtest (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date for backtest (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--outfile",
        type=str,
        help="Write JSON summary to this path",
    )
    parser.add_argument(
        "--bar_interval",
        type=str,
        default="1-DAY",
        help="Bar interval (e.g., 1-DAY, 1-HOUR, 5-MINUTE)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    strategy_name = args.strategy
    instrument_id = args.instrument_id
    
    print(f"\n{'='*80}")
    print(f"Running Continuous Futures Backtest")
    print(f"{'='*80}")
    print(f"Strategy: {strategy_name}")
    print(f"Instrument: {instrument_id}")
    print(f"Catalog: {args.catalog_path}")
    print(f"Bar Interval: {args.bar_interval}")
    print(f"Date Range: {args.start_date or 'START'} to {args.end_date or 'END'}")
    print(f"{'='*80}\n")
    
    # Import the continuous runner for nd_tt_v4
    if strategy_name == "nd_tt_v4":
        from strategies.nd_tt_v4.runner.backtest_runner.continuous_runner import (
            NdTtV4ContinuousBacktestRunner
        )
        
        runner = NdTtV4ContinuousBacktestRunner(
            catalog_path=args.catalog_path,
            start_date=args.start_date,
            end_date=args.end_date,
            bar_interval=args.bar_interval,
        )
        
        result = runner.run(instrument_id)
        
        # Print summary first
        print(f"\n{'='*80}")
        print(f"Backtest Results Summary")
        print(f"{'='*80}")
        print(f"Total P&L: {result.get('total_pnl', 0):.2f}")
        print(f"Number of Trades: {len(result.get('trades', []))}")
        print(f"Win Rate: {result.get('win_rate', 0)*100:.1f}%")
        print(f"Sharpe Ratio: {result.get('sharpe', 0):.2f}")
        print(f"Max Drawdown: {result.get('mdd_pct', 0):.2f}%")
        print(f"{'='*80}\n")
        
        # Generate report
        print("Generating reports...")
        try:
            report_controller = ReportController(mode="backtesting")
            report_path = report_controller.generate([result], strategy_name=strategy_name)
            print(f"Reports generated at: {report_path}")
            
            # Find and print report location
            from datetime import datetime
            import glob
            
            # Look for today's reports
            today = datetime.now().strftime("%Y-%m-%d")
            batch_dir = ROOT_DIR / "runlogs" / "backtesting" / "batch" / today
            
            if batch_dir.exists():
                # Find the most recent nd_tt_v4 directory
                pattern = str(batch_dir / f"*_{strategy_name}")
                matches = glob.glob(pattern)
                if matches:
                    latest = max(matches, key=lambda p: Path(p).stat().st_mtime)
                    report_path = Path(latest) / "summary.html"
                    if report_path.exists():
                        print(f"\n{'='*80}")
                        print(f"Reports available at:")
                        print(f"{'='*80}")
                        print(f"HTML Report: {report_path}")
                        print(f"CSV Export:  {Path(latest) / 'trade_details.csv'}")
                        print(f"JSON Data:   {Path(latest) / 'trade_details.json'}")
                        print(f"{'='*80}\n")
                    else:
                        print(f"Report directory created at: {latest}")
                        print(f"But summary.html not found. Check for errors.")
                else:
                    print(f"Warning: Report directory not found in {batch_dir}")
            else:
                print(f"Warning: Batch directory not created at {batch_dir}")
                
        except Exception as e:
            print(f"Error generating reports: {e}")
            import traceback
            traceback.print_exc()
        
        # Save to file if requested
        if args.outfile:
            Path(args.outfile).write_text(json.dumps(result, indent=2))
            print(f"\nResults saved to: {args.outfile}")
        
    else:
        print(f"Error: Continuous runner not implemented for strategy '{strategy_name}'")
        print(f"Only 'nd_tt_v4' is currently supported.")
        sys.exit(1)


if __name__ == "__main__":
    main()

