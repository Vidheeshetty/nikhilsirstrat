"""
Paper Trading Reporter

Real-time reporting and monitoring for paper trading sessions.
Generates live dashboards, end-of-day reports, and performance analytics.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import pandas as pd

from ..analytics import calculate_additional_metrics
from .renderers.html_paper_trading_renderer import HTMLPaperTradingRenderer

logger = logging.getLogger(__name__)


class PaperTradingReporter:
    """
    Comprehensive reporting system for paper trading.

    Features:
    - Real-time performance tracking
    - Live dashboard updates
    - End-of-day report generation
    - Multi-format output (JSON, CSV, HTML)
    - Performance analytics and metrics
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize paper trading reporter."""
        self.config = config
        self.output_dir = Path(config.get("output_dir", "runlogs/papertrading"))

        # Extract strategy name from config
        strategy_name = "unknown_strategy"
        if "strategies" in config:
            # Get the first enabled strategy name
            for strategy_key, strategy_config in config["strategies"].items():
                if strategy_config.get("enabled", False):
                    strategy_name = strategy_key.lower()
                    break
        elif "strategy_name" in config:
            strategy_name = config["strategy_name"].lower()

        # Create date-wise folder structure like backtesting
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H-%M-%S")
        self.session_id = f"{time_str}_{strategy_name}"

        # Create session directory: runlogs/papertrading/YYYY-MM-DD/HH-MM-SS_strategy_name/
        date_dir = self.output_dir / date_str
        self.session_dir = date_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Data storage
        self.session_data = {
            "start_time": datetime.now(),
            "end_time": None,
            "broker_data": [],
            "positions": [],
            "orders": [],
            "trades": [],
            "performance_snapshots": [],
            "risk_events": [],
            "system_events": [],
        }

        # Renderers
        self.html_renderer = HTMLPaperTradingRenderer()

        # Configuration
        self.realtime_updates = config.get("realtime_updates", True)
        self.update_frequency = config.get("update_frequency", 5)
        self.formats = config.get("formats", ["json", "csv", "html"])
        self.metrics = config.get(
            "metrics",
            [
                "pnl",
                "positions",
                "orders",
                "trades",
                "drawdown",
                "sharpe_ratio",
                "win_rate",
            ],
        )

        # Background tasks
        self._update_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            f"Paper trading reporter initialized for session: {self.session_id}"
        )

    async def initialize(self):
        """Initialize the reporter."""
        try:
            # Create initial session file
            await self._save_session_metadata()

            # Initialize renderers
            await self.html_renderer.initialize(self.session_dir)

            logger.info("Paper trading reporter initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize paper trading reporter: {e}")
            raise

    async def start(self):
        """Start the reporter."""
        if self._running:
            return

        self._running = True

        if self.realtime_updates:
            self._update_task = asyncio.create_task(self._update_loop())

        logger.info("Paper trading reporter started")

    async def stop(self):
        """Stop the reporter."""
        if not self._running:
            return

        self._running = False

        if self._update_task:
            self._update_task.cancel()

        # Generate final reports
        await self._generate_end_of_day_report()

        self.session_data["end_time"] = datetime.now()
        await self._save_session_data()

        logger.info("Paper trading reporter stopped")

    async def update(
        self,
        broker_data: Dict[str, Any],
        positions: List[Any],
        orders: List[Any],
        timestamp: datetime,
    ):
        """Update reporter with new data."""
        try:
            # Store snapshot
            snapshot = {
                "timestamp": timestamp,
                "broker_data": broker_data,
                "positions": [self._serialize_position(p) for p in positions],
                "orders": [self._serialize_order(o) for o in orders],
            }

            self.session_data["performance_snapshots"].append(snapshot)

            # Calculate metrics
            metrics = await self._calculate_current_metrics(snapshot)
            snapshot["metrics"] = metrics

            # Update live dashboard if enabled
            if self.realtime_updates:
                await self._update_live_dashboard(snapshot)

            # Log significant events
            await self._check_for_events(snapshot)

        except Exception as e:
            logger.error(f"Error updating paper trading reporter: {e}")

    async def log_trade(self, trade: Any):
        """Log a trade execution."""
        try:
            trade_data = self._serialize_trade(trade)
            self.session_data["trades"].append(trade_data)

            logger.info(f"Trade logged: {trade_data['trade_id']}")

        except Exception as e:
            logger.error(f"Error logging trade: {e}")

    async def log_risk_event(
        self, event_type: str, description: str, data: Dict[str, Any]
    ):
        """Log a risk management event."""
        try:
            event = {
                "timestamp": datetime.now(),
                "type": event_type,
                "description": description,
                "data": data,
            }

            self.session_data["risk_events"].append(event)
            logger.warning(f"Risk event: {event_type} - {description}")

        except Exception as e:
            logger.error(f"Error logging risk event: {e}")

    async def log_system_event(
        self, event_type: str, description: str, data: Dict[str, Any] = None
    ):
        """Log a system event."""
        try:
            event = {
                "timestamp": datetime.now(),
                "type": event_type,
                "description": description,
                "data": data or {},
            }

            self.session_data["system_events"].append(event)
            logger.info(f"System event: {event_type} - {description}")

        except Exception as e:
            logger.error(f"Error logging system event: {e}")

    async def _update_loop(self):
        """Background task for periodic updates."""
        while self._running:
            try:
                await self._periodic_update()
                await asyncio.sleep(self.update_frequency)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reporter update loop: {e}")
                await asyncio.sleep(self.update_frequency)

    async def _periodic_update(self):
        """Perform periodic updates."""
        try:
            # Save current session data
            await self._save_session_data()

            # Update live files
            if self.session_data["performance_snapshots"]:
                latest_snapshot = self.session_data["performance_snapshots"][-1]
                await self._update_live_files(latest_snapshot)

        except Exception as e:
            logger.error(f"Error in periodic update: {e}")

    async def _calculate_current_metrics(
        self, snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate current performance metrics."""
        try:
            metrics = {}

            # Extract broker data
            broker_data = snapshot["broker_data"]
            positions = snapshot["positions"]

            # Calculate P&L metrics
            total_pnl = 0
            total_unrealized_pnl = 0

            for broker_name, balance in broker_data.items():
                if isinstance(balance, dict):
                    total_pnl += balance.get("realized_pnl", 0)
                    total_unrealized_pnl += balance.get("unrealized_pnl", 0)
                elif isinstance(balance, (int, float)):
                    # Handle case where balance is a simple number
                    total_pnl += balance
                else:
                    # Skip non-numeric, non-dict values
                    logger.warning(
                        f"Unexpected balance type for {broker_name}: {type(balance)}"
                    )

            metrics["total_pnl"] = total_pnl
            metrics["unrealized_pnl"] = total_unrealized_pnl
            metrics["total_value"] = total_pnl + total_unrealized_pnl

            # Position metrics
            metrics["open_positions"] = len(
                [p for p in positions if p["quantity"] != 0]
            )
            metrics["long_positions"] = len([p for p in positions if p["quantity"] > 0])
            metrics["short_positions"] = len(
                [p for p in positions if p["quantity"] < 0]
            )

            # Trade metrics
            trades = self.session_data["trades"]
            if trades:
                winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
                losing_trades = [t for t in trades if t.get("pnl", 0) < 0]

                metrics["total_trades"] = len(trades)
                metrics["winning_trades"] = len(winning_trades)
                metrics["losing_trades"] = len(losing_trades)
                metrics["win_rate"] = len(winning_trades) / len(trades) if trades else 0

                if winning_trades:
                    metrics["avg_win"] = sum(
                        t.get("pnl", 0) for t in winning_trades
                    ) / len(winning_trades)
                if losing_trades:
                    metrics["avg_loss"] = sum(
                        t.get("pnl", 0) for t in losing_trades
                    ) / len(losing_trades)

            # Risk metrics
            snapshots = self.session_data["performance_snapshots"]
            if len(snapshots) > 1:
                pnl_series = [
                    s.get("metrics", {}).get("total_value", 0) for s in snapshots
                ]
                if pnl_series and len(pnl_series) > 1:
                    # Convert PnL series to trade-like format for calculate_additional_metrics
                    # Calculate period-to-period changes as "trades"
                    trade_like_data = []
                    for i in range(1, len(pnl_series)):
                        pnl_change = pnl_series[i] - pnl_series[i - 1]
                        trade_like_data.append({"Realised_PnL": pnl_change})

                    if trade_like_data:
                        additional_metrics = calculate_additional_metrics(
                            trade_like_data
                        )
                        metrics.update(additional_metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}

    async def _update_live_dashboard(self, snapshot: Dict[str, Any]):
        """Update live dashboard."""
        try:
            # Generate live HTML dashboard
            html_content = await self.html_renderer.render_live_dashboard(
                snapshot, self.session_data
            )

            # Save live dashboard
            live_file = self.session_dir / "live_dashboard.html"
            with open(live_file, "w") as f:
                f.write(html_content)

        except Exception as e:
            logger.error(f"Error updating live dashboard: {e}")

    async def _update_live_files(self, snapshot: Dict[str, Any]):
        """Update live data files."""
        try:
            # JSON format
            if "json" in self.formats:
                json_file = self.session_dir / "live_data.json"
                with open(json_file, "w") as f:
                    json.dump(snapshot, f, indent=2, default=str)

            # CSV format for metrics
            if "csv" in self.formats:
                metrics_file = self.session_dir / "live_metrics.csv"
                metrics = snapshot.get("metrics", {})

                # Create DataFrame
                df = pd.DataFrame([{"timestamp": snapshot["timestamp"], **metrics}])

                # Append to file or create new
                if metrics_file.exists():
                    df.to_csv(metrics_file, mode="a", header=False, index=False)
                else:
                    df.to_csv(metrics_file, index=False)

        except Exception as e:
            logger.error(f"Error updating live files: {e}")

    async def _check_for_events(self, snapshot: Dict[str, Any]):
        """Check for significant events in the snapshot."""
        try:
            metrics = snapshot.get("metrics", {})

            # Check for drawdown events
            total_value = metrics.get("total_value", 0)
            if total_value < -50000:  # Significant loss threshold
                await self.log_risk_event(
                    "LARGE_LOSS",
                    f"Portfolio value dropped to {total_value:,.2f}",
                    {"value": total_value, "timestamp": snapshot["timestamp"]},
                )

            # Check for position size events
            open_positions = metrics.get("open_positions", 0)
            if open_positions > 15:  # High position count
                await self.log_risk_event(
                    "HIGH_POSITION_COUNT",
                    f"High number of open positions: {open_positions}",
                    {"count": open_positions, "timestamp": snapshot["timestamp"]},
                )

        except Exception as e:
            logger.error(f"Error checking for events: {e}")

    async def _generate_end_of_day_report(self):
        """Generate comprehensive end-of-day report."""
        try:
            logger.info("Generating end-of-day report...")

            # Calculate final metrics
            final_metrics = {}
            if self.session_data["performance_snapshots"]:
                latest_snapshot = self.session_data["performance_snapshots"][-1]
                final_metrics = latest_snapshot.get("metrics", {})

            # Generate reports in all requested formats
            if "html" in self.formats:
                await self._generate_html_report(final_metrics)

            if "json" in self.formats:
                await self._generate_json_report(final_metrics)

            if "csv" in self.formats:
                await self._generate_csv_reports()

            logger.info("End-of-day report generation complete")

        except Exception as e:
            logger.error(f"Error generating end-of-day report: {e}")

    async def _generate_html_report(self, final_metrics: Dict[str, Any]):
        """Generate HTML report."""
        try:
            html_content = await self.html_renderer.render_full_report(
                self.session_data, final_metrics
            )

            report_file = self.session_dir / "paper_trading_report.html"
            with open(report_file, "w") as f:
                f.write(html_content)

            logger.info(f"HTML report saved: {report_file}")

        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")

    async def _generate_json_report(self, final_metrics: Dict[str, Any]):
        """Generate JSON report."""
        try:
            report_data = {
                "session_id": self.session_id,
                "session_summary": {
                    "start_time": self.session_data["start_time"],
                    "end_time": datetime.now(),
                    "duration": str(datetime.now() - self.session_data["start_time"]),
                    "final_metrics": final_metrics,
                },
                "trades": self.session_data["trades"],
                "risk_events": self.session_data["risk_events"],
                "system_events": self.session_data["system_events"],
            }

            report_file = self.session_dir / "paper_trading_report.json"
            with open(report_file, "w") as f:
                json.dump(report_data, f, indent=2, default=str)

            logger.info(f"JSON report saved: {report_file}")

        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")

    async def _generate_csv_reports(self):
        """Generate CSV reports."""
        try:
            # Trades report
            if self.session_data["trades"]:
                trades_df = pd.DataFrame(self.session_data["trades"])
                trades_file = self.session_dir / "trades.csv"
                trades_df.to_csv(trades_file, index=False)
                logger.info(f"Trades CSV saved: {trades_file}")

            # Performance snapshots
            if self.session_data["performance_snapshots"]:
                snapshots_data = []
                for snapshot in self.session_data["performance_snapshots"]:
                    row = {
                        "timestamp": snapshot["timestamp"],
                        **snapshot.get("metrics", {}),
                    }
                    snapshots_data.append(row)

                performance_df = pd.DataFrame(snapshots_data)
                performance_file = self.session_dir / "performance.csv"
                performance_df.to_csv(performance_file, index=False)
                logger.info(f"Performance CSV saved: {performance_file}")

        except Exception as e:
            logger.error(f"Error generating CSV reports: {e}")

    async def _save_session_metadata(self):
        """Save session metadata."""
        try:
            metadata = {
                "session_id": self.session_id,
                "start_time": self.session_data["start_time"],
                "config": self.config,
            }

            metadata_file = self.session_dir / "session_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving session metadata: {e}")

    async def _save_session_data(self):
        """Save current session data."""
        try:
            session_file = self.session_dir / "session_data.json"
            with open(session_file, "w") as f:
                json.dump(self.session_data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving session data: {e}")

    def _serialize_position(self, position) -> Dict[str, Any]:
        """Serialize position object."""
        return {
            "instrument_id": str(position.instrument_id),
            "quantity": position.quantity,
            "average_price": position.average_price,
            "last_price": position.last_price,
            "pnl": position.pnl,
            "unrealized_pnl": position.unrealized_pnl,
            "timestamp": position.timestamp,
        }

    def _serialize_order(self, order) -> Dict[str, Any]:
        """Serialize order object."""
        return {
            "order_id": order.order_id,
            "instrument_id": str(order.instrument_id),
            "quantity": order.quantity,
            "price": order.price,
            "order_type": str(order.order_type),
            "transaction_type": str(order.transaction_type),
            "status": str(order.status),
            "timestamp": order.timestamp,
            "filled_quantity": order.filled_quantity,
            "average_price": order.average_price,
            "broker_order_id": order.broker_order_id,
            "tags": order.tags,
        }

    def _serialize_trade(self, trade) -> Dict[str, Any]:
        """Serialize trade object."""
        return {
            "trade_id": trade.trade_id,
            "order_id": trade.order_id,
            "instrument_id": str(trade.instrument_id),
            "quantity": trade.quantity,
            "price": trade.price,
            "transaction_type": str(trade.transaction_type),
            "timestamp": trade.timestamp,
            "commission": trade.commission,
        }
