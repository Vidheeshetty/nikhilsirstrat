#!/usr/bin/env python3
"""
Report Generator for MyNSEStrategy Backtesting

Handles generation of backtest reports, logging, and summary files.
"""

import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


class ReportGenerator:
    """Generates backtest reports and summaries."""

    def __init__(self, base_dir: str = "_summary.txts"):
        self.base_dir = Path(base_dir)

    def print_and_log_results(self, result, log_file: str) -> None:
        """Print and log comprehensive backtest results."""
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
        lines.append(
            f"Elapsed Time: {result.elapsed_time:.2f} seconds ({elapsed_hours:.2f} hours)"
        )
        if result.run_started:
            lines.append(f"Run Started: {pd.Timestamp(result.run_started, unit='ns')}")
        if result.run_finished:
            lines.append(
                f"Run Finished: {pd.Timestamp(result.run_finished, unit='ns')}"
            )
        if result.backtest_start:
            lines.append(
                f"Backtest Start: {pd.Timestamp(result.backtest_start, unit='ns')}"
            )
        if result.backtest_end:
            lines.append(
                f"Backtest End: {pd.Timestamp(result.backtest_end, unit='ns')}"
            )

        # Performance metrics
        lines.append(f"Iterations: {result.iterations}")
        lines.append(f"Total Events: {result.total_events}")
        lines.append(f"Total Orders: {result.total_orders}")
        lines.append(f"Total Positions: {result.total_positions}")

        # PnL Statistics
        lines.append("\n" + "=" * 80)
        lines.append("PnL STATISTICS")
        lines.append("=" * 80)

        if result.stats_pnls:
            for currency, stats in result.stats_pnls.items():
                lines.append(f"\nCurrency: {currency}")
                lines.append("-" * 40)
                for stat_name, stat_value in stats.items():
                    if isinstance(stat_value, (int, float)):
                        if "pct" in stat_name.lower() or "rate" in stat_name.lower():
                            formatted_value = (
                                f"{stat_value:.2%}" if stat_value != 0 else "0.00%"
                            )
                        elif "pnl" in stat_name.lower():
                            formatted_value = f"{stat_value:,.2f} {currency}"
                        else:
                            formatted_value = f"{stat_value:,.2f}"
                    else:
                        formatted_value = str(stat_value)
                    lines.append(f"{stat_name}: {formatted_value}")
        else:
            lines.append("No PnL statistics available")

        # Return Statistics
        lines.append("\n" + "=" * 80)
        lines.append("RETURN STATISTICS")
        lines.append("=" * 80)

        if result.stats_returns:
            for stat_name, stat_value in result.stats_returns.items():
                if isinstance(stat_value, (int, float)):
                    if pd.isna(stat_value):
                        formatted_value = "N/A"
                    elif "ratio" in stat_name.lower() or "factor" in stat_name.lower():
                        formatted_value = f"{stat_value:.4f}"
                    elif "volatility" in stat_name.lower():
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
        with open(log_file, "a") as f:
            for line in lines:
                f.write(line + "\n")

    def print_detailed_data(self, detailed_data: Dict[str, Any], log_file: str) -> None:
        """Print and log detailed portfolio, trade, order, and strategy data."""
        lines = []

        lines.append("\n" + "=" * 80)
        lines.append("DETAILED BACKTEST DATA")
        lines.append("=" * 80)

        if "error" in detailed_data:
            lines.append(f"Error: {detailed_data['error']}")
        else:
            # Order Data
            orders = detailed_data.get("orders", [])
            lines.append(f"\nORDER DATA ({len(orders)} orders):")
            lines.append("-" * 40)
            if not orders:
                lines.append("No orders found.")
            else:
                for i, order in enumerate(orders, 1):
                    lines.append(
                        f"Order {i}: ID={order['client_order_id']}, Inst={order['instrument_id']}, Side={order['side']}, Qty={order['quantity']}, Px={order['price']}, Status={order['status']}"
                    )

            # Position Data
            positions = detailed_data.get("positions", [])
            lines.append(f"\nPOSITION DATA ({len(positions)} positions):")
            lines.append("-" * 40)
            if not positions:
                lines.append("No positions found.")
            else:
                for i, pos in enumerate(positions, 1):
                    lines.append(
                        f"Position {i}: ID={pos['id']}, Inst={pos['instrument_id']}, Side={pos['side']}, Qty={pos['quantity']}, OpenPx={pos['avg_px_open']}, PnL={pos['realized_pnl']}"
                    )

            # Trade Data
            trades = detailed_data.get("trades", [])
            lines.append(f"\nTRADE DATA ({len(trades)} trades):")
            lines.append("-" * 40)
            if not trades:
                lines.append("No trades found.")
            else:
                for i, trade in enumerate(trades, 1):
                    lines.append(
                        f"Trade {i}: ID={trade['trade_id']}, OrderID={trade['order_id']}, Inst={trade['instrument_id']}, Qty={trade['quantity']}, Px={trade['price']}"
                    )

        lines.append("\n" + "=" * 80)

        # Print to console and write to log file
        log_content = "\n".join(lines) + "\n"
        print(log_content)
        with open(log_file, "a") as f:
            f.write(log_content)

    def write_summary_with_trades(
        self, log_file: str, summary_data: Dict[str, Any], detailed_data: Dict[str, Any]
    ) -> None:
        """Write backtest summary and detailed trade data to log file."""
        with open(log_file, "a") as f:
            f.write(
                "================================================================================\n"
            )
            f.write("BACKTEST RESULTS SUMMARY\n")
            f.write(
                "================================================================================\n"
            )
            f.write(f"Instrument ID: {summary_data['instrument_id']}\n")
            f.write(
                f"Total PnL: {summary_data['pnl_total']} {summary_data['currency']}\n"
            )
            f.write(f"Total PnL %: {summary_data['pnl_pct_total']}%\n")
            f.write(f"Total Investment: {summary_data['total_investment']}\n")
            f.write(f"Total Orders: {summary_data['total_orders']}\n")
            f.write(f"Total Positions: {summary_data['total_positions']}\n")
            f.write(f"Total Trades: {summary_data['total_trades']}\n")
            f.write(f"Realized PnL: {summary_data.get('realized_pnl', '0.00')}\n")
            f.write(f"Unrealized PnL: {summary_data.get('unrealized_pnl', '0.00')}\n")
            f.write(f"Sharpe Ratio: {summary_data.get('sharpe_ratio', '0.0000')}\n")
            f.write(
                f"Starting Balance: {summary_data.get('starting_balance', 0.0):,.2f} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write(
                f"Ending Balance: {summary_data.get('ending_balance', 0.0):,.2f} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write(
                f"Free Balance: {summary_data.get('balance_free', 0.0):,.2f} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write(
                f"Locked Balance: {summary_data.get('balance_locked', 0.0):,.2f} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write("\n")
            # Add detailed trade breakdown
            if "trades" in detailed_data and detailed_data["trades"]:
                f.write(
                    "\nTRADE DATA ({}) trades:\n".format(len(detailed_data["trades"]))
                )
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

    def write_summary_only(self, log_file: str, summary_data: Dict[str, Any]) -> None:
        """Write only the backtest summary (no trade breakdown) to log file."""
        with open(log_file, "a") as f:
            f.write(
                "================================================================================\n"
            )
            f.write("BACKTEST RESULTS SUMMARY\n")
            f.write(
                "================================================================================\n"
            )
            f.write(f"Instrument ID: {summary_data['instrument_id']}\n")
            # Use _safe_float_format for all numerical values
            f.write(
                f"Total PnL: {self._safe_float_format(summary_data.get('pnl_total'), '{:,.2f}', 'N/A')} {summary_data.get('currency', 'INR')}\n"
            )
            f.write(
                f"Total PnL %: {self._safe_float_format(summary_data.get('pnl_pct_total'), '{:.2f}%', 'N/A')}\n"
            )
            f.write(
                f"Total Investment: {self._safe_float_format(summary_data.get('total_investment'), '{:,.2f}', 'N/A')} {summary_data.get('currency', 'INR')}\n"
            )
            f.write(f"Total Orders: {summary_data.get('total_orders', 'N/A')}\n")
            f.write(f"Total Positions: {summary_data.get('total_positions', 'N/A')}\n")
            f.write(f"Total Trades: {summary_data.get('total_trades', 'N/A')}\n")
            f.write(
                f"Realized PnL: {self._safe_float_format(summary_data.get('realized_pnl'), '{:,.2f}', 'N/A')}\n"
            )
            f.write(
                f"Unrealized PnL: {self._safe_float_format(summary_data.get('unrealized_pnl'), '{:,.2f}', 'N/A')}\n"
            )
            f.write(
                f"Sharpe Ratio: {self._safe_float_format(summary_data.get('sharpe_ratio'), '{:.2f}', 'N/A')}\n"
            )
            f.write(
                f"Starting Balance: {self._safe_float_format(summary_data.get('starting_balance'), '{:,.2f}', 'N/A')} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write(
                f"Ending Balance: {self._safe_float_format(summary_data.get('ending_balance'), '{:,.2f}', 'N/A')} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write(
                f"Free Balance: {self._safe_float_format(summary_data.get('balance_free'), '{:,.2f}', 'N/A')} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write(
                f"Locked Balance: {self._safe_float_format(summary_data.get('balance_locked'), '{:,.2f}', 'N/A')} {summary_data.get('base_currency', 'INR')}\n"
            )
            f.write("\n")

    def write_single_instrument_batch_log(
        self, batch_log, result: Dict[str, Any]
    ) -> None:
        """Write detailed results for a single instrument to the batch log file."""
        batch_log.write("\n" + "=" * 100 + "\n")
        batch_log.write(f"INSTRUMENT: {result['instrument_id']}\n")
        batch_log.write("=" * 100 + "\n")
        if "error" in result:
            batch_log.write(f"Error: {result['error']}\n")
        else:
            batch_log.write(f"Summary: {result.get('summary', {})}\n")
            batch_log.write(f"Detailed Data: {result.get('detailed_data', {})}\n")
            batch_log.write(f"Stats PnLs: {result.get('stats_pnls', {})}\n")
            batch_log.write(f"Account Data: {result.get('account', {})}\n")
        batch_log.write("=" * 100 + "\n")

    def create_consolidated_summary(
        self, all_results: List[Dict[str, Any]], output_file: str
    ) -> str:
        """Create consolidated summary report from multiple backtest results."""

        total_instruments = len(all_results)
        if total_instruments == 0:
            print("No results to summarize.")
            return ""

        total_orders = sum(r.get("total_orders", 0) for r in all_results)
        total_positions = sum(r.get("total_positions", 0) for r in all_results)
        total_trades = sum(r.get("total_trades", 0) for r in all_results)
        total_investment = sum(
            self._parse_currency_value(r.get("total_investment", "0.0 INR"))
            for r in all_results
        )
        total_pnl = sum(
            self._parse_currency_value(r.get("pnl_total", "0.0")) for r in all_results
        )
        overall_pnl_percentage = (
            (total_pnl / total_investment) * 100 if total_investment > 0 else 0.0
        )

        # Calculate totals for other columns
        total_realized_pnl = sum(float(r.get("realized_pnl", 0.0)) for r in all_results)
        total_unrealized_pnl = sum(
            float(r.get("unrealized_pnl", 0.0)) for r in all_results
        )
        # For Sharpe Ratio, calculate average, handling potential non-numeric values
        sharpe_ratios = [
            float(r.get("sharpe_ratio", 0.0))
            for r in all_results
            if isinstance(r.get("sharpe_ratio"), (int, float))
        ]
        total_sharpe_ratio = (
            sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0.0
        )

        total_start_balance = sum(
            float(r.get("starting_balance", 0.0)) for r in all_results
        )
        total_end_balance = sum(
            float(r.get("ending_balance", 0.0)) for r in all_results
        )

        with open(output_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("CONSOLIDATED BACKTEST SUMMARY REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Total Instruments Tested: {total_instruments}\n\n")

            f.write("OVERALL SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Orders Placed: {total_orders}\n")
            f.write(f"Total Positions Opened: {total_positions}\n")
            f.write(f"Total Trades Executed: {total_trades}\n")
            f.write(f"Total Investment: {total_investment:,.2f} INR\n")
            f.write(f"Total PnL: {total_pnl:,.2f} INR\n")
            f.write(f"Overall PnL %: {overall_pnl_percentage:.2f}%\n\n")

            f.write("INSTRUMENT-WISE SUMMARY\n")
            f.write("-" * 190 + "\n")
            f.write(
                f"{'Instrument':<40} | {'Orders':>8} | {'Positions':>10} | {'Trades':>8} | {'Investment':>15} | {'PnL':>12} | {'PnL%':>7} | {'Realized':>14} | {'Unrealized':>15} | {'Sharpe':>8} | {'Start Bal':>10} | {'End Bal':>10}\n"
            )
            f.write("-" * 190 + "\n")

            def _safe_float_format(value, format_string, default_value="N/A"):
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    return default_value
                try:
                    return format_string.format(float(value))
                except (ValueError, TypeError):
                    return default_value

            # Add TOTAL row at the beginning of the table
            f.write(
                f"{'TOTAL':<40} | {total_orders:>8} | {total_positions:>10} | {total_trades:>8} | "
                f"{_safe_float_format(total_investment, '{:>15.2f}', 'N/A')} | "
                f"{_safe_float_format(total_pnl, '{:>12.2f}', 'N/A')} | "
                f"{_safe_float_format(overall_pnl_percentage, '{:>7.2f}', 'N/A')} | "
                f"{_safe_float_format(total_realized_pnl, '{:>14.2f}', 'N/A')} | "
                f"{_safe_float_format(total_unrealized_pnl, '{:>15.2f}', 'N/A')} | "
                f"{_safe_float_format(total_sharpe_ratio, '{:>8.2f}', 'N/A')} | "
                f"{_safe_float_format(total_start_balance, '{:>10.2f}', 'N/A')} | "
                f"{_safe_float_format(total_end_balance, '{:>10.2f}', 'N/A')}\n"
            )
            f.write("-" * 190 + "\n")

            for result in all_results:
                instrument_id_short = (
                    result["instrument_id"][:37] + "..."
                    if len(result["instrument_id"]) > 40
                    else result["instrument_id"]
                )
                f.write(
                    f"{instrument_id_short:<40} | {result['total_orders']:>8} | {result['total_positions']:>10} | {result['total_trades']:>8} | "
                    f"{_safe_float_format(result.get('total_investment', 0.0), '{:>15.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('pnl_total', 0.0), '{:>12.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('pnl_pct_total', 0.0), '{:>7.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('realized_pnl', 0.0), '{:>14.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('unrealized_pnl', 0.0), '{:>15.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('sharpe_ratio', 0.0), '{:>8.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('starting_balance', 0.0), '{:>10.2f}', 'N/A')} | "
                    f"{_safe_float_format(result.get('ending_balance', 0.0), '{:>10.2f}', 'N/A')}\n"
                )
            f.write("-" * 190 + "\n")
            # Add TOTAL row at the end of the table
            f.write(
                f"{'TOTAL':<40} | {total_orders:>8} | {total_positions:>10} | {total_trades:>8} | "
                f"{_safe_float_format(total_investment, '{:>15.2f}', 'N/A')} | "
                f"{_safe_float_format(total_pnl, '{:>12.2f}', 'N/A')} | "
                f"{_safe_float_format(overall_pnl_percentage, '{:>7.2f}', 'N/A')} | "
                f"{_safe_float_format(total_realized_pnl, '{:>14.2f}', 'N/A')} | "
                f"{_safe_float_format(total_unrealized_pnl, '{:>15.2f}', 'N/A')} | "
                f"{_safe_float_format(total_sharpe_ratio, '{:>8.2f}', 'N/A')} | "
                f"{_safe_float_format(total_start_balance, '{:>10.2f}', 'N/A')} | "
                f"{_safe_float_format(total_end_balance, '{:>10.2f}', 'N/A')}\n"
            )
            f.write("=" * 190 + "\n")
            f.write("\n\n")

        return output_file

    def _parse_currency_value(self, value_str: str) -> float:
        """Parses a currency string (e.g., "1,000.00 INR") into a float."""
        if isinstance(value_str, (int, float)):
            return float(value_str)
        try:
            # Remove currency symbols, commas, and strip whitespace
            clean_value = (
                value_str.replace("INR", "").replace("₹", "").replace(",", "").strip()
            )
            return float(clean_value)
        except (ValueError, TypeError):
            return 0.0  # Return 0.0 if parsing fails

    def create_tabular_summary(
        self, all_results: List[Dict[str, Any]], output_file: str
    ):
        """Create a tabular summary report for all instruments."""
        if not all_results:
            return

        # Create DataFrame for tabular format
        df_data = []
        for result in all_results:
            df_data.append(
                {
                    "Instrument ID": result.get("instrument_id", "N/A"),
                    "Total Orders": result.get("total_orders", 0),
                    "Total Positions": result.get("total_positions", 0),
                    "Total Trades": result.get("total_trades", 0),
                    "Total Investment": result.get("total_investment", "0.00 INR"),
                    "PnL (Total)": result.get("pnl_total", "0.00"),
                    "PnL (%)": result.get("pnl_pct_total", "0.0000"),
                    "Realized PnL": result.get("realized_pnl", "0.00"),
                    "Unrealized PnL": result.get("unrealized_pnl", "0.00"),
                    "Sharpe Ratio": result.get("sharpe_ratio", "0.0000"),
                    "Starting Balance": f"{result.get('starting_balance', 0.0):,.2f}",
                    "Ending Balance": f"{result.get('ending_balance', 0.0):,.2f}",
                    "Free Balance": f"{result.get('balance_free', 0.0):,.2f}",
                    "Locked Balance": f"{result.get('balance_locked', 0.0):,.2f}",
                    "Currency": result.get("base_currency", "INR"),
                }
            )

        pd.DataFrame(df_data)

        # Calculate summary statistics
        total_instruments = len(all_results)
        total_orders = sum(r.get("total_orders", 0) for r in all_results)
        total_positions = sum(r.get("total_positions", 0) for r in all_results)
        total_trades = sum(r.get("total_trades", 0) for r in all_results)

        # Calculate total PnL
        total_pnl = 0.0
        total_investment = 0.0
        for result in all_results:
            try:
                pnl_str = result.get("pnl_total", "0.00")
                pnl = (
                    float(pnl_str.replace(",", ""))
                    if isinstance(pnl_str, str)
                    else float(pnl_str)
                )
                total_pnl += pnl

                # Extract investment amount
                inv_str = result.get("total_investment", "0.00 INR")
                if isinstance(inv_str, str):
                    inv_parts = inv_str.split()
                    if len(inv_parts) >= 1:
                        inv = float(inv_parts[0].replace(",", ""))
                        total_investment += inv
            except (ValueError, TypeError):
                pass

        # Calculate overall PnL percentage
        overall_pnl_pct = (
            (total_pnl / total_investment * 100) if total_investment > 0 else 0.0
        )

        # Get account details from first result
        first_result = all_results[0] if all_results else {}
        starting_balance = first_result.get("starting_balance", 0.0)
        ending_balance = first_result.get("ending_balance", 0.0)
        currency = first_result.get("base_currency", "INR")

        # Write tabular report
        with open(output_file, "w") as f:
            f.write("=" * 120 + "\n")
            f.write("BACKTEST RESULTS - ALL INSTRUMENTS (TABULAR FORMAT)\n")
            f.write("=" * 120 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Instruments Tested: {total_instruments}\n\n")

            # Overall Summary
            f.write("OVERALL SUMMARY\n")
            f.write("-" * 50 + "\n")
            f.write(f"Total Orders Placed: {total_orders:,}\n")
            f.write(f"Total Positions Opened: {total_positions:,}\n")
            f.write(f"Total Trades Executed: {total_trades:,}\n")
            f.write(f"Total Investment: {total_investment:,.2f} {currency}\n")
            f.write(f"Total PnL: {total_pnl:,.2f} {currency}\n")
            f.write(f"Overall PnL%: {overall_pnl_pct:.4f}%\n")
            f.write(f"Starting Balance: {starting_balance:,.2f} {currency}\n")
            f.write(f"Ending Balance: {ending_balance:,.2f} {currency}\n")
            f.write(
                f"Net Account Change: {ending_balance - starting_balance:,.2f} {currency}\n\n"
            )

            # Tabular Data
            f.write("DETAILED RESULTS BY INSTRUMENT\n")
            f.write("-" * 120 + "\n")

            # Write header
            f.write(
                f"{'Instrument ID':<25} {'Orders':<6} {'Pos':<6} {'Trades':<6} "
                f"{'Investment':<12} {'PnL':<10} {'PnL%':<8} "
                f"{'Realized':<10} {'Unrealized':<11} {'Sharpe':<8} "
                f"{'Start Bal':<10} {'End Bal':<10} {'Free Bal':<10} {'Locked Bal':<10}\n"
            )
            f.write("-" * 150 + "\n")

            # Write data rows
            for result in all_results:
                instrument_id = result.get("instrument_id", "N/A")
                if len(instrument_id) > 24:
                    instrument_id = instrument_id[:21] + "..."

                f.write(
                    f"{instrument_id:<25} "
                    f"{result.get('total_orders', 0):<6} "
                    f"{result.get('total_positions', 0):<6} "
                    f"{result.get('total_trades', 0):<6} "
                    f"{result.get('total_investment', '0.00 INR'):<12} "
                    f"{result.get('pnl_total', '0.00'):<10} "
                    f"{result.get('pnl_pct_total', '0.0000'):<8} "
                    f"{result.get('realized_pnl', '0.00'):<10} "
                    f"{result.get('unrealized_pnl', '0.00'):<11} "
                    f"{result.get('sharpe_ratio', '0.0000'):<8} "
                    f"{result.get('starting_balance', 0.0):<10,.0f} "
                    f"{result.get('ending_balance', 0.0):<10,.0f} "
                    f"{result.get('balance_free', 0.0):<10,.0f} "
                    f"{result.get('balance_locked', 0.0):<10,.0f}\n"
                )

            f.write("-" * 150 + "\n")

            # Performance Statistics
            f.write("\nPERFORMANCE STATISTICS\n")
            f.write("-" * 50 + "\n")

            # Calculate statistics
            pnl_values = []
            for result in all_results:
                try:
                    pnl_str = result.get("pnl_total", "0.00")
                    pnl = (
                        float(pnl_str.replace(",", ""))
                        if isinstance(pnl_str, str)
                        else float(pnl_str)
                    )
                    pnl_values.append(pnl)
                except (ValueError, TypeError):
                    pnl_values.append(0.0)

            if pnl_values:
                profitable_trades = sum(1 for pnl in pnl_values if pnl > 0)
                losing_trades = sum(1 for pnl in pnl_values if pnl < 0)
                win_rate = (
                    (profitable_trades / len(pnl_values) * 100) if pnl_values else 0
                )

                f.write(f"Profitable Instruments: {profitable_trades}\n")
                f.write(f"Losing Instruments: {losing_trades}\n")
                f.write(f"Win Rate: {win_rate:.2f}%\n")
                f.write(f"Best PnL: {max(pnl_values):,.2f} {currency}\n")
                f.write(f"Worst PnL: {min(pnl_values):,.2f} {currency}\n")
                f.write(
                    f"Average PnL: {sum(pnl_values) / len(pnl_values):,.2f} {currency}\n"
                )

            f.write("\n" + "=" * 120 + "\n")
            f.write("END OF TABULAR REPORT\n")
            f.write("=" * 120 + "\n")

        print(f"Tabular summary created: {output_file}")

    def print_order_data(self, detailed_data: Dict[str, Any], log_file: str) -> None:
        """Print and log only ORDER DATA section."""
        lines = []
        orders = detailed_data.get("orders", [])
        lines.append("\nORDER DATA ({}) orders:".format(len(orders)))
        lines.append("-" * 40)
        if not orders:
            lines.append("No orders found.")
        else:
            for i, order in enumerate(orders, 1):
                lines.append(
                    f"Order {i}: ID={order['client_order_id']}, Inst={order['instrument_id']}, Side={order['side']}, Qty={order['quantity']}, Px={order['price']}, Status={order['status']}"
                )
        lines.append("\n" + "=" * 80)
        with open(log_file, "a") as f:
            f.write("\n".join(lines) + "\n")

    def print_position_data(self, detailed_data: Dict[str, Any], log_file: str) -> None:
        """Print and log only POSITION DATA section."""
        lines = []
        positions = detailed_data.get("positions", [])
        lines.append("\nPOSITION DATA ({}) positions:".format(len(positions)))
        lines.append("-" * 40)
        if not positions:
            lines.append("No positions found.")
        else:
            for i, pos in enumerate(positions, 1):
                lines.append(
                    f"Position {i}: ID={pos['id']}, Inst={pos['instrument_id']}, Side={pos['side']}, Qty={pos['quantity']}, OpenPx={pos['avg_px_open']}, PnL={pos['realized_pnl']}"
                )
        lines.append("\n" + "=" * 80)
        with open(log_file, "a") as f:
            f.write("\n".join(lines) + "\n")

    def print_trade_data(self, detailed_data: Dict[str, Any], log_file: str) -> None:
        """Print and log only TRADE DATA section."""
        lines = []
        trades = detailed_data.get("trades", [])
        lines.append("\nTRADE DATA ({}) trades:".format(len(trades)))
        lines.append("-" * 40)
        if not trades:
            lines.append("No trades found.")
        else:
            for i, trade in enumerate(trades, 1):
                lines.append(
                    f"Trade {i}: ID={trade['trade_id']}, OrderID={trade['order_id']}, Inst={trade['instrument_id']}, Qty={trade['quantity']}, Px={trade['price']}"
                )
        lines.append("\n" + "=" * 80)
        with open(log_file, "a") as f:
            f.write("\n".join(lines) + "\n")

    def write_batch_results_summary(
        self, log_file: str, all_results: List[Dict[str, Any]]
    ):
        """Write a detailed BACKTEST RESULTS SUMMARY for batch runs, aggregating totals and averages."""
        total_orders = sum(r.get("total_orders", 0) for r in all_results)
        total_positions = sum(r.get("total_positions", 0) for r in all_results)
        total_trades = sum(r.get("total_trades", 0) for r in all_results)
        total_investment = sum(
            float(str(r.get("total_investment", "0.0")).split()[0]) for r in all_results
        )
        total_pnl = sum(
            float(r.get("pnl_total", "0.00").replace(",", "")) for r in all_results
        )
        total_realized_pnl = sum(
            float(r.get("realized_pnl", "0.00").replace(",", "")) for r in all_results
        )
        total_unrealized_pnl = sum(
            float(r.get("unrealized_pnl", "0.00").replace(",", "")) for r in all_results
        )
        avg_sharpe = sum(
            float(r.get("sharpe_ratio", "0.0000"))
            for r in all_results
            if r.get("sharpe_ratio")
        ) / max(1, len([r for r in all_results if r.get("sharpe_ratio")]))
        total_starting_balance = sum(
            float(r.get("starting_balance", 0.0)) for r in all_results
        )
        total_ending_balance = sum(
            float(r.get("ending_balance", 0.0)) for r in all_results
        )
        total_free_balance = sum(float(r.get("balance_free", 0.0)) for r in all_results)
        total_locked_balance = sum(
            float(r.get("balance_locked", 0.0)) for r in all_results
        )
        currency = all_results[0].get("currency", "INR") if all_results else "INR"
        base_currency = (
            all_results[0].get("base_currency", "INR") if all_results else "INR"
        )
        pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0.0

        with open(log_file, "a") as f:
            f.write(
                "================================================================================\n"
            )
            f.write("BACKTEST RESULTS SUMMARY\n")
            f.write(
                "================================================================================\n"
            )
            f.write(f"Total PnL: {total_pnl:.2f} {currency}\n")
            f.write(f"Total PnL %: {pnl_pct:.4f}%\n")
            f.write(f"Total Investment: {total_investment:.2f} {currency}\n")
            f.write(f"Total Orders: {total_orders}\n")
            f.write(f"Total Positions: {total_positions}\n")
            f.write(f"Total Trades: {total_trades}\n")
            f.write(f"Realized PnL: {total_realized_pnl:.2f}\n")
            f.write(f"Unrealized PnL: {total_unrealized_pnl:.2f}\n")
            f.write(f"Sharpe Ratio (avg): {avg_sharpe:.4f}\n")
            f.write(
                f"Starting Balance (sum): {total_starting_balance:,.2f} {base_currency}\n"
            )
            f.write(
                f"Ending Balance (sum): {total_ending_balance:,.2f} {base_currency}\n"
            )
            f.write(f"Free Balance (sum): {total_free_balance:,.2f} {base_currency}\n")
            f.write(
                f"Locked Balance (sum): {total_locked_balance:,.2f} {base_currency}\n"
            )
            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")
