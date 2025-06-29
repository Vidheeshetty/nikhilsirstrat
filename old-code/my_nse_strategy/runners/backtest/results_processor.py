#!/usr/bin/env python3
"""
Results Processor for MyNSEStrategy Backtesting

Handles extraction and processing of backtest results, trades, orders, and positions.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from nautilus_trader.model.currencies import INR
from datetime import datetime
from nautilus_trader.analysis.statistics.sharpe_ratio import SharpeRatio
from nautilus_trader.analysis.statistics.returns_volatility import ReturnsVolatility


class ResultsProcessor:
    """Processes and extracts data from backtest results."""

    def __init__(self, pnl_currency: str = "INR"):
        self.pnl_currency = pnl_currency

    def extract_detailed_data(self, engine, result, log_file: str) -> Dict[str, Any]:
        """Extract detailed portfolio, trade, order, and strategy data."""
        detailed_data = {}

        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        debug_log_path = os.path.join(log_dir, "debug_extraction.log")

        try:
            # Generate reports from the trader
            fills_report = engine.trader.generate_order_fills_report()
            positions_report = engine.trader.generate_positions_report()

            # Extract account details
            account_data = self._extract_account_data(engine, result)
            detailed_data["account"] = account_data

            # Process fills (trades)
            trades = self._process_trades(fills_report)
            detailed_data["trades"] = trades

            # Process positions
            positions = self._process_positions(positions_report)
            detailed_data["positions"] = positions

            # Process orders
            orders = self._process_orders(engine.cache.orders())
            detailed_data["orders"] = orders

            # PATCH: Extract last available price for each instrument from engine data
            last_prices = {}
            try:
                # Try to get last price from engine's data (quote ticks)
                if hasattr(engine, "data") and hasattr(engine.data, "quote_ticks"):
                    for instrument_id, ticks in engine.data.quote_ticks.items():
                        if hasattr(ticks, "__len__") and len(ticks) > 0:
                            last_tick = ticks[-1]
                            # Try to get price from tick (bid/ask/last)
                            price = None
                            for key in ["last", "close", "bid", "ask", "price"]:
                                if hasattr(last_tick, key):
                                    price = getattr(last_tick, key)
                                    if price is not None:
                                        break
                            if price is not None:
                                last_prices[str(instrument_id)] = float(price)
            except Exception as e:
                print(f"[WARNING] Could not extract last prices from engine data: {e}")
            detailed_data["last_prices"] = last_prices

            # --- PATCH: Reconstruct equity curve from closed positions ---
            # Build a time series of account balance after each position close
            equity_curve = []
            timestamps = []
            running_balance = (
                account_data["starting_balance"] if account_data else 1_000_000.0
            )
            for pos in positions:
                ts_closed = pos.get("ts_closed")
                realized_pnl = pos.get("realized_pnl", "0.0")
                try:
                    realized_pnl_val = float(
                        str(realized_pnl)
                        .replace("INR", "")
                        .replace("₹", "")
                        .replace(",", "")
                        .strip()
                    )
                except Exception:
                    realized_pnl_val = 0.0
                running_balance += realized_pnl_val
                if ts_closed and ts_closed != "N/A":
                    timestamps.append(pd.to_datetime(ts_closed))
                    equity_curve.append(running_balance)
            # If no positions closed, just use start/end
            if not equity_curve:
                equity_curve = [
                    account_data["starting_balance"],
                    account_data["ending_balance"],
                ]
                timestamps = [pd.Timestamp.now(), pd.Timestamp.now()]
            detailed_data["equity_curve"] = pd.Series(equity_curve, index=timestamps)

        except Exception as e:
            import traceback

            error_message = (
                f"Error extracting detailed data: {e}\n{traceback.format_exc()}"
            )
            detailed_data["error"] = error_message
            with open(debug_log_path, "a") as dbg:
                dbg.write(error_message + "\n")

        return detailed_data

    def _extract_account_data(self, engine, result=None) -> dict:
        """Extracts account data, preferring BacktestResult fields if available."""
        # Always use known initial capital for starting_balance
        STARTING_BALANCE = 1_000_000.00
        # Try to use BacktestResult account_balances DataFrame if provided
        if (
            result is not None
            and hasattr(result, "account_balances")
            and result.account_balances is not None
        ):
            try:
                # Use the final_balances method if available
                if hasattr(result, "final_balances"):
                    final_balances = result.final_balances()
                    # Assume only one venue/currency for single-instrument
                    if (
                        hasattr(final_balances, "values")
                        and len(final_balances.values) > 0
                    ):
                        ending_balance = float(final_balances.values[-1])
                        return {
                            "account_id": getattr(result, "account_id", "N/A"),
                            "base_currency": getattr(result, "base_currency", "N/A"),
                            "starting_balance": STARTING_BALANCE,
                            "ending_balance": ending_balance,
                            "balance_free": ending_balance,  # Assume all free if not split
                            "balance_locked": 0.0,
                        }
            except Exception as e:
                print(
                    f"[WARNING] Failed to extract balances from BacktestResult.account_balances: {e}"
                )
        accounts = engine.cache.accounts() if hasattr(engine.cache, "accounts") else []
        if accounts and len(accounts) > 0:
            account = accounts[0]
            ending_balance = float(
                account.balance_total()
                if callable(getattr(account, "balance_total", None))
                else getattr(account, "balance_total", 0.0)
            )
            return {
                "account_id": getattr(account, "account_id", "N/A"),
                "base_currency": getattr(account, "base_currency", "N/A"),
                "starting_balance": STARTING_BALANCE,
                "ending_balance": ending_balance,
                "balance_free": float(
                    account.balance_free()
                    if callable(getattr(account, "balance_free", None))
                    else getattr(account, "balance_free", 0.0)
                ),
                "balance_locked": float(
                    account.balance_locked()
                    if callable(getattr(account, "balance_locked", None))
                    else getattr(account, "balance_locked", 0.0)
                ),
            }
        else:
            print(
                "[WARNING] No account found in engine.cache.accounts(). Returning zeros."
            )
            return {
                "account_id": "N/A",
                "base_currency": "N/A",
                "starting_balance": STARTING_BALANCE,
                "ending_balance": 0.0,
                "balance_free": 0.0,
                "balance_locked": 0.0,
            }

    def _process_trades(self, fills_report) -> List[Dict[str, Any]]:
        """Process trade data from fills report."""
        trades = []
        for _, row in fills_report.iterrows():
            trades.append(
                {
                    "trade_id": row.get("last_trade_id", "N/A"),
                    "order_id": row.name,  # The index is the client_order_id
                    "instrument_id": str(row.get("instrument_id", "N/A")),
                    "side": str(row.get("side", "N/A")),
                    "quantity": str(row.get("filled_qty", "0")),
                    "price": str(row.get("avg_px", "0.0")),
                    "commission": str(row.get("commissions", "0.0")),
                    "ts_event": pd.Timestamp(row.get("ts_last"), unit="ns").isoformat()
                    if pd.notna(row.get("ts_last"))
                    else "N/A",
                }
            )
        return trades

    def _process_positions(self, positions_report) -> List[Dict[str, Any]]:
        """Process position data from positions report."""
        positions = []
        for _, row in positions_report.iterrows():
            positions.append(
                {
                    "id": row.name,  # The index is the position_id
                    "instrument_id": str(row.get("instrument_id", "N/A")),
                    "side": str(row.get("side", "N/A")),
                    "quantity": str(row.get("quantity", "0")),
                    "avg_px_open": str(row.get("avg_px_open", "0.0")),
                    "avg_px_close": str(row.get("avg_px_close", "N/A")),
                    "realized_pnl": str(row.get("realized_pnl", "0.0")),
                    "ts_opened": pd.Timestamp(
                        row.get("ts_opened"), unit="ns"
                    ).isoformat()
                    if pd.notna(row.get("ts_opened"))
                    else "N/A",
                    "ts_closed": pd.Timestamp(
                        row.get("ts_closed"), unit="ns"
                    ).isoformat()
                    if pd.notna(row.get("ts_closed"))
                    else "N/A",
                }
            )
        return positions

    def _process_orders(self, orders) -> List[Dict[str, Any]]:
        """Process order data from cache."""
        return [
            {
                "client_order_id": str(o.client_order_id),
                "instrument_id": str(o.instrument_id),
                "side": str(o.side),
                "order_type": str(o.order_type),
                "quantity": str(o.quantity),
                "price": str(o.price) if hasattr(o, "price") and o.price else "N/A",
                "status": str(o.status),
                "ts_init": pd.Timestamp(o.ts_init, unit="ns").isoformat()
                if o.ts_init
                else "N/A",
            }
            for o in orders
        ]

    def extract_returns_series(self, result, detailed_data) -> pd.Series:
        """Extract or reconstruct returns series for advanced stats."""
        # Try to get equity curve from result if available
        equity_curve = getattr(result, "equity_curve", None)
        if equity_curve is not None and isinstance(
            equity_curve, (pd.Series, np.ndarray, list)
        ):
            if isinstance(equity_curve, np.ndarray) or isinstance(equity_curve, list):
                equity_curve = pd.Series(equity_curve)
            returns = equity_curve.pct_change().dropna()
            return returns
        # Fallback: reconstruct from balances if possible
        account = detailed_data.get("account", {})
        start = account.get("starting_balance", None)
        end = account.get("ending_balance", None)
        if start is not None and end is not None and start > 0:
            # Fake a two-point return series
            returns = pd.Series([0, (end - start) / start])
            return returns
        # Fallback: cannot compute
        return pd.Series(dtype=float)

    def extract_pnl_data(self, result, detailed_data=None) -> Dict[str, float]:
        """Extract PnL data from result object, including realized/unrealized and Sharpe ratio."""

        def parse_pnl(val):
            if isinstance(val, (float, int)):
                return float(val)
            if isinstance(val, str):
                # Remove currency suffix and commas
                val = val.replace("INR", "").replace("₹", "").replace(",", "").strip()
                try:
                    return float(val)
                except Exception:
                    return 0.0
            return 0.0

        # Debug: print stats_pnls and direct attributes
        # print("\n[DEBUG] result.stats_pnls:", getattr(result, 'stats_pnls', None))
        # print("[DEBUG] result attributes:")
        # for attr in ['total_pnl', 'pnl_pct', 'realized_pnl', 'unrealized_pnl', 'sharpe_ratio']:
        #     print(f"  {attr}: {getattr(result, attr, 'N/A')}")
        # Try stats_pnls dict first
        stats = None
        if hasattr(result, "stats_pnls") and isinstance(result.stats_pnls, dict):
            stats = result.stats_pnls.get(self.pnl_currency, {})

        def get_stat(stats, key):
            val = stats.get(key) if stats else None
            fval = parse_pnl(val)
            return fval if fval is not None else "N/A"

        total_pnl = get_stat(stats, "PnL (total)")
        pnl_pct = get_stat(stats, "PnL% (total)")
        realized_pnl = get_stat(stats, "PnL (realized)")
        unrealized_pnl = get_stat(stats, "PnL (unrealized)")
        sharpe_ratio = get_stat(stats, "Sharpe Ratio (252 days)")
        # Fallback: try direct result attributes if present
        if total_pnl == "N/A":
            total_pnl = parse_pnl(getattr(result, "total_pnl", None))
            if total_pnl is None:
                total_pnl = "N/A"
        if pnl_pct == "N/A":
            pnl_pct = parse_pnl(getattr(result, "pnl_pct", None))
            if pnl_pct is None:
                pnl_pct = "N/A"
        if realized_pnl in [None, "N/A"] or abs(realized_pnl) < 1e-8:
            # Fallback: sum realized_pnl from closed positions (side == 'FLAT')
            if detailed_data is not None:
                positions = detailed_data.get("positions", [])
                realized_sum = 0.0
                for pos in positions:
                    side_val = pos.get("Side", pos.get("side", "")).upper()
                    if side_val == "FLAT":
                        val = (
                            str(pos.get("realized_pnl", "0.0"))
                            .replace("INR", "")
                            .replace("₹", "")
                            .replace(",", "")
                            .strip()
                        )
                        try:
                            realized_sum += float(val)
                        except Exception:
                            pass
                realized_pnl = realized_sum
        if unrealized_pnl == "N/A":
            unrealized_pnl = parse_pnl(getattr(result, "unrealized_pnl", None))
        # Fallback: sum unrealized PnL from open positions if unrealized_pnl is zero or None
        if (
            unrealized_pnl in [None, "N/A"] or abs(unrealized_pnl) < 1e-8
        ) and detailed_data is not None:
            positions = detailed_data.get("positions", [])
            # PATCH: Use last available price for open positions if possible
            last_prices = detailed_data.get(
                "last_prices", {}
            )  # Should be a dict: instrument_id -> last_price
            open_positions = []
            unrealized_sum = 0.0
            unrealized_values = []
            raw_unrealized_values = []
            for pos in positions:
                side_val = pos.get("Side", pos.get("side", "")).upper()
                qty_val = float(pos.get("quantity", 0))
                instrument_id = pos.get("instrument_id", None)
                avg_px_open = float(pos.get("avg_px_open", 0.0))
                if side_val != "FLAT" and qty_val > 0 and instrument_id:
                    # Try to get last price for this instrument
                    last_price = None
                    if last_prices and instrument_id in last_prices:
                        last_price = float(last_prices[instrument_id])
                    # Fallback: use avg_px_open if no last price
                    if last_price is None:
                        last_price = avg_px_open
                    # Calculate unrealized PnL
                    if side_val == "LONG":
                        unrealized = (last_price - avg_px_open) * qty_val
                    elif side_val == "SHORT":
                        unrealized = (avg_px_open - last_price) * qty_val
                    else:
                        unrealized = 0.0
                    # print(f"[DEBUG] Open position {instrument_id}: side={side_val}, qty={qty_val}, avg_px_open={avg_px_open}, last_price={last_price}, unrealized_pnl={unrealized}")
                    unrealized_sum += unrealized
                    unrealized_values.append(unrealized)
                    open_positions.append(pos)
            # print(f"[DEBUG] Open positions for unrealized PnL extraction (using last price): {open_positions}")
            # print(f"[DEBUG] Fallback unrealized PnL sum (using last price): {unrealized_sum}, values: {unrealized_values}")
            unrealized_pnl = unrealized_sum
        if sharpe_ratio == "N/A":
            # Try to compute Sharpe Ratio from returns
            returns = self.extract_returns_series(result, detailed_data or {})
            if not returns.empty:
                try:
                    sharpe = SharpeRatio(period=252).calculate_from_returns(returns)
                    sharpe_ratio = (
                        float(sharpe)
                        if sharpe is not None and not np.isnan(sharpe)
                        else "N/A"
                    )
                except Exception as e:
                    # print(f"[WARNING] Failed to compute Sharpe Ratio: {e}")
                    sharpe_ratio = "N/A"
        return {
            "total_pnl": total_pnl,
            "pnl_percentage": pnl_pct,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "sharpe_ratio": sharpe_ratio,
        }

    def calculate_investment(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate total investment from BUY trades."""
        total_investment = 0.0
        for trade in trades:
            if str(trade.get("side")) == "BUY":
                try:
                    price = float(trade.get("price", "0.0"))
                    quantity = float(trade.get("quantity", "0"))
                    total_investment += price * quantity
                except (ValueError, TypeError):
                    pass
        return total_investment

    def create_summary_data(
        self,
        result,
        detailed_data: Dict[str, Any],
        instrument_id: str,
        batch_mode: bool = False,
    ) -> Dict[str, Any]:
        """Create summary data dictionary. For batch_mode, use pre-extracted stats/account fields if present. For single runs, always calculate pnl_pct_total as (total_pnl / total_investment) * 100."""

        def fmt(val, fmtstr):
            try:
                if isinstance(val, (float, int)):
                    return fmtstr.format(val)
                return str(val)
            except Exception:
                return str(val)

        # For batch runs, use pre-extracted stats/account if present
        if batch_mode and isinstance(result, dict):
            stats_pnls = result.get("stats_pnls", None)
            account_data = result.get("account", detailed_data.get("account", {}))
            if stats_pnls and isinstance(stats_pnls, dict):
                stats = stats_pnls.get(self.pnl_currency, {})
                total_pnl = float(stats.get("PnL (total)", 0.0))
                pnl_pct = float(stats.get("PnL% (total)", 0.0)) * 100
                realized_pnl = float(stats.get("PnL (realized)", 0.0))
                unrealized_pnl = float(stats.get("PnL (unrealized)", 0.0))
                sharpe_ratio = float(stats.get("Sharpe Ratio (252 days)", 0.0))
            else:
                # Fallback: try direct keys on result dict
                total_pnl = float(result.get("total_pnl", 0.0))
                pnl_pct = float(result.get("pnl_pct", 0.0))
                realized_pnl = float(result.get("realized_pnl", 0.0))
                unrealized_pnl = float(result.get("unrealized_pnl", 0.0))
                sharpe_ratio = float(result.get("sharpe_ratio", 0.0))
            total_investment = self.calculate_investment(
                detailed_data.get("trades", [])
            )
            summary = {
                "instrument_id": instrument_id,
                "total_orders": result.get("total_orders", 0),
                "total_positions": result.get("total_positions", 0),
                "total_trades": len(detailed_data.get("trades", [])),
                "total_investment": fmt(
                    total_investment, "{:.2f} " + self.pnl_currency
                ),
                "pnl_total": fmt(total_pnl, "{:.2f}"),
                # For batch, keep using stats_pnls or fallback value
                "pnl_pct_total": fmt(pnl_pct, "{:.4f}"),
                "realized_pnl": fmt(realized_pnl, "{:.2f}"),
                "unrealized_pnl": fmt(unrealized_pnl, "{:.2f}"),
                "sharpe_ratio": fmt(sharpe_ratio, "{:.4f}"),
                "currency": self.pnl_currency,
            }
            if account_data and "error" not in account_data:
                summary.update(
                    {
                        "starting_balance": account_data.get("starting_balance", 0.0),
                        "ending_balance": account_data.get("ending_balance", 0.0),
                        "balance_free": account_data.get("balance_free", 0.0),
                        "balance_locked": account_data.get("balance_locked", 0.0),
                        "account_id": account_data.get("account_id", "N/A"),
                        "base_currency": account_data.get(
                            "base_currency", self.pnl_currency
                        ),
                    }
                )
            else:
                summary.update(
                    {
                        "starting_balance": 0.0,
                        "ending_balance": 0.0,
                        "balance_free": 0.0,
                        "balance_locked": 0.0,
                        "account_id": "N/A",
                        "base_currency": self.pnl_currency,
                    }
                )
            return summary
        # Default: single-instrument or non-batch
        pnl_data = self.extract_pnl_data(result, detailed_data)
        total_investment = self.calculate_investment(detailed_data.get("trades", []))
        account_data = detailed_data.get("account", {})
        total_pnl = pnl_data["total_pnl"]
        # Always calculate pnl_pct_total as (total_pnl / total_investment) * 100 for single runs
        if isinstance(total_pnl, (float, int)) and total_investment > 0:
            pnl_pct_total = (total_pnl / total_investment) * 100
        else:
            pnl_pct_total = "N/A"
        summary = {
            "instrument_id": instrument_id,
            "total_orders": getattr(result, "total_orders", 0),
            "total_positions": getattr(result, "total_positions", 0),
            "total_trades": len(detailed_data.get("trades", [])),
            "total_investment": fmt(total_investment, "{:.2f} " + self.pnl_currency),
            "pnl_total": fmt(total_pnl, "{:.2f}"),
            "pnl_pct_total": fmt(pnl_pct_total, "{:.4f}"),
            "realized_pnl": fmt(pnl_data["realized_pnl"], "{:.2f}"),
            "unrealized_pnl": fmt(pnl_data["unrealized_pnl"], "{:.2f}"),
            "sharpe_ratio": fmt(pnl_data["sharpe_ratio"], "{:.4f}"),
            "currency": self.pnl_currency,
        }
        if account_data and "error" not in account_data:
            summary.update(
                {
                    "starting_balance": account_data.get("starting_balance", 0.0),
                    "ending_balance": account_data.get("ending_balance", 0.0),
                    "balance_free": account_data.get("balance_free", 0.0),
                    "balance_locked": account_data.get("balance_locked", 0.0),
                    "account_id": account_data.get("account_id", "N/A"),
                    "base_currency": account_data.get(
                        "base_currency", self.pnl_currency
                    ),
                }
            )
        else:
            summary.update(
                {
                    "starting_balance": 0.0,
                    "ending_balance": 0.0,
                    "balance_free": 0.0,
                    "balance_locked": 0.0,
                    "account_id": "N/A",
                    "base_currency": self.pnl_currency,
                }
            )
        return summary
