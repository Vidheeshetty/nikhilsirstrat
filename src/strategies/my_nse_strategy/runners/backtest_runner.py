#!/usr/bin/env python3
"""
Simple Backtest Runner for MyNSEStrategy

This module provides a simplified backtesting interface that reads configuration
from YAML and allows command-line overrides.

Usage:
    # Run with default config
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE"
    
    # Override specific parameters
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --start_time "2025-06-18T12:00:00"
    
    # Use custom config file
    python backtest_runner.py --instrument_id "BANKNIFTY.OPT.26Jun2025.40500.CALL.NSE" --config_file "custom_config.yaml"
"""

import sys
import os
from pathlib import Path
import argparse
import yaml
from datetime import datetime
import pandas as pd
import types
import logging

# Add parent directories to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from nautilus_trader.backtest.config import (
    BacktestVenueConfig, BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig
)
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.currencies import INR
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from nautilus_trader.model.enums import OmsType, AccountType, BookType
from nautilus_trader.model.objects import Money, Currency

# Import strategy
from strategies.my_nse_strategy.strategy import MyNSEStrategy
from strategies.my_nse_strategy.config import MyNSEStrategyConfig


def load_config_from_file(config_file: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def print_and_log_results(result, log_file):
    """Print and log comprehensive backtest results including portfolio, trades, orders, and strategy data."""
    lines = []
    
    # Basic run information
    lines.append("=" * 80)
    lines.append("BACKTEST RESULTS SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Run ID: {result.run_id}")
    lines.append(f"Trader ID: {result.trader_id}")
    lines.append(f"Machine ID: {result.machine_id}")
    lines.append(f"Run Config ID: {result.run_config_id}")
    lines.append(f"Instance ID: {result.instance_id}")
    
    # Time information
    elapsed_hours = result.elapsed_time / 3600
    lines.append(f"Elapsed Time: {result.elapsed_time:.2f} seconds ({elapsed_hours:.2f} hours)")
    if result.run_started:
        lines.append(f"Run Started: {pd.Timestamp(result.run_started, unit='ns')}")
    if result.run_finished:
        lines.append(f"Run Finished: {pd.Timestamp(result.run_finished, unit='ns')}")
    if result.backtest_start:
        lines.append(f"Backtest Start: {pd.Timestamp(result.backtest_start, unit='ns')}")
    if result.backtest_end:
        lines.append(f"Backtest End: {pd.Timestamp(result.backtest_end, unit='ns')}")
    
    # Performance metrics
    lines.append(f"Iterations: {result.iterations}")
    lines.append(f"Total Events: {result.total_events}")
    lines.append(f"Total Orders: {result.total_orders}")
    lines.append(f"Total Positions: {result.total_positions}")
    
    # PnL Statistics - formatted nicely
    lines.append("\n" + "=" * 80)
    lines.append("PnL STATISTICS")
    lines.append("=" * 80)
    
    if result.stats_pnls:
        for currency, stats in result.stats_pnls.items():
            lines.append(f"\nCurrency: {currency}")
            lines.append("-" * 40)
            for stat_name, stat_value in stats.items():
                if isinstance(stat_value, (int, float)):
                    if 'pct' in stat_name.lower() or 'rate' in stat_name.lower():
                        formatted_value = f"{stat_value:.2%}" if stat_value != 0 else "0.00%"
                    elif 'pnl' in stat_name.lower():
                        formatted_value = f"{stat_value:,.2f} {currency}"
                    else:
                        formatted_value = f"{stat_value:,.2f}"
                else:
                    formatted_value = str(stat_value)
                lines.append(f"{stat_name}: {formatted_value}")
    else:
        lines.append("No PnL statistics available")
    
    # Return Statistics - formatted nicely
    lines.append("\n" + "=" * 80)
    lines.append("RETURN STATISTICS")
    lines.append("=" * 80)
    
    if result.stats_returns:
        for stat_name, stat_value in result.stats_returns.items():
            if isinstance(stat_value, (int, float)):
                if pd.isna(stat_value):
                    formatted_value = "N/A"
                elif 'ratio' in stat_name.lower() or 'factor' in stat_name.lower():
                    formatted_value = f"{stat_value:.4f}"
                elif 'volatility' in stat_name.lower():
                    formatted_value = f"{stat_value:.4f}"
                else:
                    formatted_value = f"{stat_value:.4f}"
            else:
                formatted_value = str(stat_value)
            lines.append(f"{stat_name}: {formatted_value}")
    else:
        lines.append("No return statistics available")
    
    lines.append("\n" + "=" * 80)
    lines.append("END OF RESULTS")
    lines.append("=" * 80)
    
    # Print to console
    for line in lines:
        print(line)
    
    # Write to log file
    with open(log_file, 'a') as f:
        for line in lines:
            f.write(line + '\n')


def safe_dict_items(obj):
    if isinstance(obj, dict):
        return obj.items()
    return []


def get_detailed_backtest_data(engine, result, log_file):
    """Extract detailed portfolio, trade, order, and strategy data from the backtest engine."""
    detailed_data = {}
    
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    debug_log_path = os.path.join(log_dir, "debug_extraction.log")

    try:
        # Generate reports from the trader
        fills_report = engine.trader.generate_order_fills_report()
        positions_report = engine.trader.generate_positions_report()
        
        # Process fills (trades) - using correct column names from debug output
        trades = []
        for _, row in fills_report.iterrows():
            trades.append({
                "trade_id": row.get("last_trade_id", "N/A"),
                "order_id": row.name,  # The index is the client_order_id
                "instrument_id": str(row.get("instrument_id", "N/A")),
                "side": str(row.get("side", "N/A")),
                "quantity": str(row.get("filled_qty", "0")),
                "price": str(row.get("avg_px", "0.0")),
                "commission": str(row.get("commissions", "0.0")),
                "ts_event": pd.Timestamp(row.get("ts_last"), unit='ns').isoformat() if pd.notna(row.get("ts_last")) else "N/A",
            })
        detailed_data["trades"] = trades

        # Process positions
        positions = []
        for _, row in positions_report.iterrows():
            positions.append({
                "id": row.name,  # The index is the position_id
                "instrument_id": str(row.get("instrument_id", "N/A")),
                "side": str(row.get("side", "N/A")),
                "quantity": str(row.get("quantity", "0")),
                "avg_px_open": str(row.get("avg_px_open", "0.0")),
                "avg_px_close": str(row.get("avg_px_close", "N/A")),
                "realized_pnl": str(row.get("realized_pnl", "0.0")),
                "ts_opened": pd.Timestamp(row.get("ts_opened"), unit='ns').isoformat() if pd.notna(row.get("ts_opened")) else "N/A",
                "ts_closed": pd.Timestamp(row.get("ts_closed"), unit='ns').isoformat() if pd.notna(row.get("ts_closed")) else "N/A",
            })
        detailed_data["positions"] = positions
        
        # Orders can still be retrieved from the cache as it's a list of objects
        orders = engine.cache.orders()
        detailed_data["orders"] = [
            {
                "client_order_id": str(o.client_order_id),
                "instrument_id": str(o.instrument_id),
                "side": str(o.side),
                "order_type": str(o.order_type),
                "quantity": str(o.quantity),
                "price": str(o.price) if hasattr(o, 'price') and o.price else "N/A",
                "status": str(o.status),
                "ts_init": pd.Timestamp(o.ts_init, unit='ns').isoformat() if o.ts_init else "N/A"
            } for o in orders
        ]

    except Exception as e:
        import traceback
        error_message = f"Error extracting detailed data: {e}\n{traceback.format_exc()}"
        detailed_data["error"] = error_message
        with open(debug_log_path, 'a') as dbg:
            dbg.write(error_message + "\n")
            
    return detailed_data


def print_detailed_data(detailed_data, log_file):
    """Print and log detailed portfolio, trade, order, and strategy data."""
    lines = []
    
    lines.append("\n" + "=" * 80)
    lines.append("DETAILED BACKTEST DATA")
    lines.append("=" * 80)
    
    if "error" in detailed_data:
        lines.append(f"Error: {detailed_data['error']}")
    else:
        # Account Data
        if "account" in detailed_data:
            lines.append("\nACCOUNT DATA:")
            lines.append("-" * 40)
            account_data = detailed_data["account"]
            lines.append(f"  Account ID: {account_data.get('account_id', 'N/A')}")
            lines.append(f"  Type: {account_data.get('account_type', 'N/A')}")
            lines.append(f"  Base Currency: {account_data.get('base_currency', 'N/A')}")
            for balance in account_data.get('balances', []):
                lines.append(f"  Balance ({balance.get('currency', '')}): {balance.get('total', '0.0')} (Free: {balance.get('free', '0.0')}, Locked: {balance.get('locked', '0.0')})")

        # Order Data
        orders = detailed_data.get("orders", [])
        lines.append(f"\nORDER DATA ({len(orders)} orders):")
        lines.append("-" * 40)
        if not orders:
            lines.append("No orders found.")
        else:
            for i, order in enumerate(orders, 1):
                lines.append(f"Order {i}: ID={order['client_order_id']}, Inst={order['instrument_id']}, Side={order['side']}, Qty={order['quantity']}, Px={order['price']}, Status={order['status']}")

        # Position Data
        positions = detailed_data.get("positions", [])
        lines.append(f"\nPOSITION DATA ({len(positions)} positions):")
        lines.append("-" * 40)
        if not positions:
            lines.append("No positions found.")
        else:
            for i, pos in enumerate(positions, 1):
                lines.append(f"Position {i}: ID={pos['id']}, Inst={pos['instrument_id']}, Side={pos['side']}, Qty={pos['quantity']}, OpenPx={pos['avg_px_open']}, PnL={pos['realized_pnl']}")
        
        # Trade Data
        trades = detailed_data.get("trades", [])
        lines.append(f"\nTRADE DATA ({len(trades)} trades):")
        lines.append("-" * 40)
        if not trades:
            lines.append("No trades found.")
        else:
            for i, trade in enumerate(trades, 1):
                lines.append(f"Trade {i}: ID={trade['trade_id']}, OrderID={trade['order_id']}, Inst={trade['instrument_id']}, Qty={trade['quantity']}, Px={trade['price']}")

    lines.append("\n" + "=" * 80)
    
    # Print to console and write to log file
    log_content = "\n".join(lines) + "\n"
    print(log_content)
    with open(log_file, 'a') as f:
        f.write(log_content)


def parse_currency_value(value_str):
    """Extracts the float value from a currency string like '123.45 INR'."""
    if isinstance(value_str, str):
        try:
            return float(value_str.split()[0])
        except (ValueError, IndexError):
            return 0.0
    return float(value_str)


def create_consolidated_summary(all_results, overall_summary_file):
    """Creates a consolidated summary report from a list of backtest results."""
    
    total_instruments = len(all_results)
    if total_instruments == 0:
        print("No results to summarize.")
        return

    # Aggregate results
    total_orders = sum(r.get("total_orders", 0) for r in all_results)
    total_positions = sum(r.get("total_positions", 0) for r in all_results)
    total_trades = sum(r.get("total_trades", 0) for r in all_results)
    total_investment = sum(parse_currency_value(r.get("total_investment", "0.0 INR")) for r in all_results)
    total_pnl = sum(parse_currency_value(r.get("total_pnl", "0.0 INR")) for r in all_results)
    
    # Calculate overall PnL%
    overall_pnl_percentage = (total_pnl / total_investment) * 100 if total_investment > 0 else 0.0

    with open(overall_summary_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("CONSOLIDATED BACKTEST SUMMARY REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {pd.Timestamp.now()}\n")
        f.write(f"Total Instruments Tested: {total_instruments}\n\n")
        
        f.write("OVERALL SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total Orders Placed: {total_orders}\n")
        f.write(f"Total Positions Opened: {total_positions}\n")
        f.write(f"Total Trades Executed: {total_trades}\n")
        f.write(f"Total Investment: {total_investment:.2f} INR\n")
        f.write(f"Total PnL: {total_pnl:.2f} INR\n")
        f.write(f"Overall PnL %: {overall_pnl_percentage:.4f}%\n\n")

        f.write("INSTRUMENT-WISE SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Instrument':<40} | {'Orders':>8} | {'Positions':>10} | {'Trades':>8} | {'Investment':>15} | {'PnL':>12} | {'PnL%':>8}\n")
        f.write("-" * 110 + "\n")
        for result in all_results:
            instrument_id_short = result['instrument_id'].split('.CALL.')[0]
            f.write(
                f"{instrument_id_short:<40} | {result['total_orders']:>8} | {result['total_positions']:>10} | {result['total_trades']:>8} | "
                f"{result['total_investment']:>15} | {result['total_pnl']:>12} | {result['total_pnl_percentage']:>8}\n"
            )
        f.write("=" * 110 + "\n")

    return overall_summary_file


def run_backtest(
    instrument_id: str,
    config_file: str,
    start_time: str,
    end_time: str,
    log_file: str,
):
    """Run backtest for a single instrument."""
    
    # Set default currency
    pnl_currency = "INR"

    # Load configuration
    config = load_config_from_file(config_file)
    
    # Override instrument_id if provided
    if instrument_id and instrument_id.lower() != "all":
        config["instrument_id"] = instrument_id
    
    # Create catalog
    catalog = ParquetDataCatalog("catalog-data/my_nse_strategy/catalog")

    # Create backtest engine
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id="BACKTESTER-001"
        ),
    )
    
    # Add venue before adding instrument
    engine.add_venue(
        venue=Venue('NSE'),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(1_000_000, INR)], # Use Money object with int
        base_currency=INR,
        book_type=BookType.L1_MBP,
    )
    # Add instruments
    instruments = catalog.instruments(
        instrument_ids=[config["instrument_id"]],
        as_nautilus=True,
    )
    engine.add_instrument(instruments[0])
    
    # Add data
    data = catalog.quote_ticks(
        instrument_ids=[config["instrument_id"]],
        start=start_time,
        end=end_time,
        as_nautilus=True,
    )
    engine.add_data(data)
    
    # Prepare config for MyNSEStrategyConfig
    config["instrument_id"] = InstrumentId.from_str(config["instrument_id"])
    strategy_config = MyNSEStrategyConfig(**config)
    
    # Add strategy
    strategy = MyNSEStrategy(config=strategy_config)
    engine.add_strategy(strategy)
    
    # Run backtest
    engine.run()
    
    # Get results
    result = engine.get_result()
    
    # Extract detailed data
    detailed_data = get_detailed_backtest_data(engine, result, log_file)
    
    # Print and log results
    print_and_log_results(result, log_file)
    print_detailed_data(detailed_data, log_file)
    
    # Calculate investment
    total_investment = 0.0
    if "trades" in detailed_data:
        for trade in detailed_data["trades"]:
            if str(trade.get("side")) == "BUY":  # Correctly check the order side
                try:
                    price = float(trade.get("price", "0.0"))
                    quantity = float(trade.get("quantity", "0"))
                    total_investment += price * quantity
                except (ValueError, TypeError):
                    pass  # Ignore if price or quantity are not valid numbers

    # Extract PnL information
    total_pnl = 0.0
    pnl_pct = 0.0
    
    # Helper function to safely convert values to float (handles numpy types)
    def to_float(val):
        if hasattr(val, 'item'):
            return float(val.item())
        return float(val)
    
    if result.stats_pnls and isinstance(result.stats_pnls, dict):
        stats = result.stats_pnls.get(pnl_currency, {})
        total_pnl = to_float(stats.get('PnL (total)', 0.0))
        pnl_pct = to_float(stats.get('PnL% (total)', 0.0)) * 100

    # Create a summary dictionary
    summary_data = {
        "instrument_id": instrument_id,
        "total_orders": result.total_orders,
        "total_positions": result.total_positions,
        "total_trades": len(detailed_data.get("trades", [])),
        "total_investment": f"{total_investment:.2f} {pnl_currency}",
        "pnl_total": f"{total_pnl:.2f}",
        "pnl_pct_total": f"{pnl_pct:.4f}",
        "currency": pnl_currency,
    }

    # Write summary with detailed trade data
    write_summary_with_trades(log_file, summary_data, detailed_data)
    
    return summary_data


def write_summary_with_trades(log_file, summary_data, detailed_data):
    """Writes the backtest summary and detailed trade data to a log file."""
    with open(log_file, "w") as f:
        f.write("================================================================================\n")
        f.write("BACKTEST RESULTS SUMMARY\n")
        f.write("================================================================================\n")
        f.write(f"Instrument ID: {summary_data['instrument_id']}\n")
        f.write(f"Total PnL: {summary_data['pnl_total']} {summary_data['currency']}\n")
        f.write(f"Total PnL %: {summary_data['pnl_pct_total']}%\n")
        f.write(f"Total Investment: {summary_data['total_investment']}\n")
        f.write(f"Total Orders: {summary_data['total_orders']}\n")
        f.write(f"Total Positions: {summary_data['total_positions']}\n")
        f.write(f"Total Trades: {summary_data['total_trades']}\n")
        f.write("\n")
        
        # Add detailed trade breakdown
        if "trades" in detailed_data and detailed_data["trades"]:
            f.write("\nTRADE DATA ({}) trades:\n".format(len(detailed_data["trades"])))
            f.write("-" * 80 + "\n")
            for i, trade in enumerate(detailed_data["trades"], 1):
                f.write(
                    f"Trade {i}: ID={trade.get('trade_id', 'N/A')}, "
                    f"OrderID={trade.get('order_id', 'N/A')}, "
                    f"Side={trade.get('side', 'N/A')}, "
                    f"Qty={trade.get('quantity', 'N/A')}, "
                    f"Price={trade.get('price', 'N/A')}\n"
                )
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


def get_all_instrument_ids(catalog_path: str) -> list[str]:
    """Get all instrument IDs from the data catalog."""
    
    instrument_ids = set()
    
    # Define the data type directories to scan
    data_types = ["quote_tick", "option_contract"]
    
    for data_type in data_types:
        data_path = Path(catalog_path) / "data" / data_type
        
        if not data_path.exists() or not data_path.is_dir():
            print(f"Warning: Directory not found at {data_path}")
            continue
            
        # Get all subdirectories, which are assumed to be instrument IDs
        for d in data_path.iterdir():
            if d.is_dir():
                instrument_ids.add(d.name)
                
    return sorted(list(instrument_ids))


def main():
    parser = argparse.ArgumentParser(description="Run backtest for NSE strategy")
    parser.add_argument(
        "--instrument_id",
        type=str,
        required=True,
        help="Instrument ID to backtest, or 'all' for all instruments",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="src/strategies/my_nse_strategy/config/strategy.yaml",
        help="Path to the strategy configuration file.",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to the log file. If not specified, a new one will be created.",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default=None,
        help="Backtest start time in ISO format (e.g., '2025-01-01T00:00:00Z'). Overrides config.",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default=None,
        help="Backtest end time in ISO format (e.g., '2025-01-01T23:59:59Z'). Overrides config.",
    )

    args = parser.parse_args()

    # Setup base directory for logs and summaries
    base_dir = Path("_summary.txts") / datetime.now().strftime("%Y-%m-%d")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%H-%M-%S")

    if args.instrument_id.lower() == 'all':
        # Run for all instruments and create a consolidated summary
        all_instrument_ids = get_all_instrument_ids("catalog-data/my_nse_strategy/catalog")
        all_results = []
        
        for i, instrument_id in enumerate(all_instrument_ids):
            print(f"\n{'='*40}\nRunning backtest for instrument {i+1}/{len(all_instrument_ids)}: {instrument_id}\n{'='*40}")
            
            # Create a unique log file for each instrument run
            log_file_path = base_dir / f"{timestamp}-backtest-{instrument_id.replace('/', '_')}.log"
            
            try:
                result_summary = run_backtest(
                    instrument_id=instrument_id,
                    config_file=args.config,
                    start_time=args.start_time,
                    end_time=args.end_time,
                    log_file=str(log_file_path),
                )
                if result_summary:
                    all_results.append(result_summary)
            except Exception as e:
                print(f"ERROR: Backtest for {instrument_id} failed: {e}")

        # Create the final consolidated summary report
        if all_results:
            consolidated_summary_path = base_dir / f"{timestamp}-consolidated-summary.txt"
            create_consolidated_summary(all_results, str(consolidated_summary_path))
            print(f"\nConsolidated summary report created at: {consolidated_summary_path}")

    else:
        # Run for a single instrument
        log_file_path = base_dir / f"{timestamp}-backtest-{args.instrument_id.replace('/', '_')}.log"
        run_backtest(
            instrument_id=args.instrument_id,
            config_file=args.config,
            start_time=args.start_time,
            end_time=args.end_time,
            log_file=str(log_file_path),
        )


if __name__ == "__main__":
    main()