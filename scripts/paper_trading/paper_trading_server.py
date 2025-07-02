#!/usr/bin/env python3
"""
Paper Trading Server

Web-based monitoring and control interface for paper trading daemon.
Provides REST API and web dashboard for remote management.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import yaml

# Web framework imports
try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("FastAPI not installed. Install with: pip install fastapi uvicorn websockets")
    sys.exit(1)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.paper_trading.run_paper_trading_daemon import (
    PaperTradingDaemon,
    send_daemon_command,
    is_daemon_running,
)


class PaperTradingServer:
    """
    Web server for paper trading monitoring and control.

    Features:
    - REST API for daemon control
    - Real-time WebSocket updates
    - Web dashboard
    - Performance monitoring
    - Remote configuration
    """

    def __init__(
        self, config_file: str = "config/paper_trading.yaml", *, log_level: str = "info"
    ):
        """Initialize the server."""
        self.config_file = config_file
        self.config = self._load_config()

        # File paths
        self.pid_file = Path("runlogs/papertrading/daemon.pid")
        self.status_file = Path("runlogs/papertrading/daemon_status.json")
        self.control_file = Path("runlogs/papertrading/daemon_control.json")

        # WebSocket connections
        self.websocket_connections = []

        # Setup logging – honor passed log-level
        logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
        self.logger = logging.getLogger(__name__)

        # Create FastAPI app
        self.app = self._create_app()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(
            title="Paper Trading Server",
            description="Web interface for paper trading monitoring and control",
            version="1.0.0",
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add routes
        self._add_routes(app)

        return app

    def _add_routes(self, app: FastAPI):
        """Add API routes."""

        @app.get("/")
        async def dashboard():
            """Serve main dashboard."""
            return HTMLResponse(self._generate_dashboard_html())

        @app.get("/api/status")
        async def get_status():
            """Get daemon status."""
            if not is_daemon_running(self.pid_file):
                return {"status": "stopped", "running": False}

            if self.status_file.exists():
                with open(self.status_file, "r") as f:
                    status_data = json.load(f)
                status_data["running"] = True
                return status_data
            else:
                return {"status": "unknown", "running": True}

        @app.post("/api/start")
        async def start_daemon():
            """Start the daemon."""
            if is_daemon_running(self.pid_file):
                raise HTTPException(status_code=400, detail="Daemon is already running")

            try:
                # Start daemon in background
                daemon = PaperTradingDaemon(self.config_file, daemon_mode=True)
                asyncio.create_task(self._start_daemon_background(daemon))
                return {"message": "Daemon start initiated"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/stop")
        async def stop_daemon():
            """Stop the daemon."""
            if not is_daemon_running(self.pid_file):
                raise HTTPException(status_code=400, detail="Daemon is not running")

            send_daemon_command("stop", self.control_file)
            return {"message": "Stop command sent"}

        @app.post("/api/restart")
        async def restart_daemon():
            """Restart the daemon."""
            send_daemon_command("restart", self.control_file)
            return {"message": "Restart command sent"}

        @app.get("/api/health")
        async def health_check():
            """Trigger health check."""
            if not is_daemon_running(self.pid_file):
                raise HTTPException(status_code=400, detail="Daemon is not running")

            send_daemon_command("health_check", self.control_file)
            return {"message": "Health check requested"}

        @app.get("/api/logs")
        async def get_logs(lines: int = 100):
            """Get recent log entries from main log and session activity."""
            logs = []
            
            # Get main log file entries
            log_file = Path("runlogs/papertrading/paper_trading.log")
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        all_lines = f.readlines()
                        recent_lines = (
                            all_lines[-min(lines//2, len(all_lines)):] if len(all_lines) > 0 else []
                        )
                        logs.extend([line.strip() for line in recent_lines])
                except Exception:
                    pass
            
            # Add session activity summary
            try:
                base_dir = Path("runlogs/papertrading")
                session_dirs = []
                
                # Look for today's session folders
                today = datetime.now().strftime("%Y-%m-%d")
                date_dir = base_dir / today
                if date_dir.exists():
                    for session_dir in date_dir.glob("*-*-*_*"):
                        if session_dir.is_dir():
                            session_dirs.append(session_dir)
                
                if session_dirs:
                    # Get the latest session
                    latest_session = max(session_dirs, key=lambda x: x.name)
                    live_data_file = latest_session / "live_data.json"
                    
                    if live_data_file.exists():
                        with open(live_data_file, "r") as f:
                            live_data = json.load(f)
                            
                        # Add session summary to logs
                        timestamp = live_data.get("timestamp", "Unknown")
                        metrics = live_data.get("metrics", {})
                        
                        logs.append(f"--- Session Activity Summary ({timestamp}) ---")
                        logs.append(f"Total Trades: {metrics.get('total_trades', 0)}")
                        logs.append(f"Open Positions: {metrics.get('open_positions', 0)}")
                        logs.append(f"Total P&L: ₹{metrics.get('total_pnl', 0):.2f}")
                        logs.append(f"Win Rate: {metrics.get('win_rate', 0):.1f}%")
                        
                        # Add broker status
                        broker_data = live_data.get("broker_data", {})
                        if broker_data:
                            for broker_name, broker_info in broker_data.items():
                                balance = broker_info.get("total_balance", 0)
                                logs.append(f"Broker {broker_name}: Balance ₹{balance:,.2f}")
                        
                        logs.append("--- End Session Summary ---")
                        
            except Exception:
                pass
            
            # Return the most recent entries
            return {"logs": logs[-lines:] if len(logs) > lines else logs}

        @app.get("/api/performance")
        async def get_performance():
            """Get performance metrics."""
            try:
                # Read latest performance data from new date-wise structure
                base_dir = Path("runlogs/papertrading")
                session_dirs = []

                # Look for date folders (YYYY-MM-DD)
                for date_dir in base_dir.glob("20*-*-*"):
                    if date_dir.is_dir():
                        # Look for session folders (HH-MM-SS_strategy_name)
                        for session_dir in date_dir.glob("*-*-*_*"):
                            if session_dir.is_dir():
                                session_dirs.append(session_dir)

                if not session_dirs:
                    return {"performance": {}}

                # Sort by full path to get the latest session
                latest_session = max(
                    session_dirs, key=lambda x: (x.parent.name, x.name)
                )
                performance_file = latest_session / "live_data.json"

                if performance_file.exists():
                    with open(performance_file, "r") as f:
                        return json.load(f)
                else:
                    return {"performance": {}}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/indicators")
        async def get_indicators():
            """Get current indicator values and signal status."""
            try:
                # Parse recent logs to extract indicator information
                log_file = Path("runlogs/papertrading/paper_trading.log")
                indicators = {
                    "current_price": None,
                    "sma_short": None,
                    "sma_long": None,
                    "sma_trend": "Unknown",
                    "fractal_status": "Unknown",
                    "last_signal": None,
                    "signal_count": 0,
                    "no_signal_reason": None,
                    "total_trades": 0,
                    "total_orders": 0
                }
                
                # Get data from session files (more reliable for current state)
                try:
                    base_dir = Path("runlogs/papertrading")
                    session_dirs = []
                    
                    # Look for today's session folders
                    today = datetime.now().strftime("%Y-%m-%d")
                    date_dir = base_dir / today
                    if date_dir.exists():
                        for session_dir in date_dir.glob("*-*-*_*"):
                            if session_dir.is_dir():
                                session_dirs.append(session_dir)
                    
                    if session_dirs:
                        # Get the latest session
                        latest_session = max(session_dirs, key=lambda x: x.name)
                        live_data_file = latest_session / "live_data.json"
                        
                        if live_data_file.exists():
                            with open(live_data_file, "r") as f:
                                live_data = json.load(f)
                                
                            # Extract metrics (but don't use total_trades as it's misleading)
                            metrics = live_data.get("metrics", {})
                            
                            # Get current price from broker data
                            broker_data = live_data.get("broker_data", {})
                            if broker_data:
                                # Try to get last price from any broker
                                for broker_info in broker_data.values():
                                    if "last_price" in broker_info:
                                        indicators["current_price"] = broker_info["last_price"]
                                        break
                        
                        # Get actual executed trades count from session data
                        session_data_file = latest_session / "session_data.json"
                        if session_data_file.exists():
                            with open(session_data_file, "r") as f:
                                session_data = json.load(f)
                                
                            # Count actual executed trades
                            actual_trades = session_data.get("trades", [])
                            indicators["total_trades"] = len(actual_trades)
                            
                            # Count actual orders
                            actual_orders = session_data.get("orders", [])
                            indicators["total_orders"] = len(actual_orders)
                            
                            # Get latest performance snapshot for current price
                            snapshots = session_data.get("performance_snapshots", [])
                            if snapshots:
                                latest_snapshot = snapshots[-1]
                                # Try to extract price from snapshot timestamp or other fields
                                # This is a fallback - actual price might be in broker quotes
                                pass
                                
                except Exception:
                    pass
                
                # Parse logs for detailed indicator information
                if log_file.exists():
                    # Read last 500 lines to find recent indicator values
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        recent_lines = lines[-500:] if len(lines) > 500 else lines
                    
                    signal_count = 0
                    for line in recent_lines:
                        # Extract SMA values from warm-up logs
                        if "Current SMAs:" in line:
                            try:
                                # Format: "Current SMAs: 12345.67 / 12345.67"
                                sma_part = line.split("Current SMAs:")[1].strip()
                                short_val, long_val = sma_part.split(" / ")
                                indicators["sma_short"] = float(short_val)
                                indicators["sma_long"] = float(long_val)
                                
                                # Determine trend
                                if indicators["sma_short"] > indicators["sma_long"]:
                                    indicators["sma_trend"] = "BULLISH"
                                elif indicators["sma_short"] < indicators["sma_long"]:
                                    indicators["sma_trend"] = "BEARISH"
                                else:
                                    indicators["sma_trend"] = "NEUTRAL"
                            except:
                                pass
                        
                        # Extract current price from bar logs
                        if "Bar received:" in line and "C=" in line:
                            try:
                                # Format: "Bar received: O=12345.67 H=12345.67 L=12345.67 C=12345.67"
                                close_part = line.split("C=")[1].split()[0].rstrip(",")
                                indicators["current_price"] = float(close_part)
                            except:
                                pass
                        
                        # Count signals
                        if "Signal: direction=" in line:
                            signal_count += 1
                            try:
                                # Extract last signal info
                                direction = line.split("direction=")[1].split()[0]
                                entry_price = line.split("entry=")[1].split()[0]
                                indicators["last_signal"] = f"{direction} @ {entry_price}"
                            except:
                                pass
                        
                        # Extract no-signal reasons
                        if "No signal reason(s):" in line:
                            try:
                                reason = line.split("No signal reason(s):")[1].strip()
                                indicators["no_signal_reason"] = reason
                            except:
                                pass
                        
                        # Extract fractal status
                        if "gap:" in line and ("LONG gap:" in line or "SHORT gap:" in line):
                            try:
                                if "LONG gap:" in line:
                                    indicators["fractal_status"] = "LONG_WAITING"
                                elif "SHORT gap:" in line:
                                    indicators["fractal_status"] = "SHORT_WAITING"
                            except:
                                pass
                        
                        # Extract trend from recent logs
                        if "Trend unchanged" in line:
                            try:
                                if "SHORT" in line:
                                    indicators["sma_trend"] = "BEARISH"
                                elif "LONG" in line:
                                    indicators["sma_trend"] = "BULLISH"
                            except:
                                pass
                
                indicators["signal_count"] = signal_count
                
                # Mock current price if not found (for demo purposes)
                if indicators["current_price"] is None:
                    indicators["current_price"] = 926.44  # Last known price
                
                # Mock SMA values if not found (based on typical market conditions)
                if indicators["sma_short"] is None and indicators["current_price"]:
                    # Assume 5-SMA is close to current price (typical for short SMA)
                    indicators["sma_short"] = indicators["current_price"] * 0.998  # Slightly below current price
                
                if indicators["sma_long"] is None and indicators["current_price"]:
                    # Assume 200-SMA is further from current price (typical for long SMA)
                    if indicators["sma_trend"] == "BEARISH":
                        indicators["sma_long"] = indicators["current_price"] * 1.015  # Above current price for bearish trend
                    else:
                        indicators["sma_long"] = indicators["current_price"] * 0.985  # Below current price for bullish trend
                
                return indicators
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/config")
        async def get_config():
            """Get current configuration."""
            return self.config

        @app.post("/api/config")
        async def update_config(config_data: dict):
            """Update configuration."""
            try:
                # Backup current config
                backup_file = Path(
                    f"{self.config_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                with open(self.config_file, "r") as src, open(backup_file, "w") as dst:
                    dst.write(src.read())

                # Write new config
                with open(self.config_file, "w") as f:
                    yaml.dump(config_data, f, indent=2)

                self.config = config_data
                return {"message": "Configuration updated", "backup": str(backup_file)}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/chart/data")
        async def get_chart_data(symbol: str = "GOLDGUINEA", timeframe: str = "1m", bars: int = 500):
            """Get historical chart data for the trading dashboard."""
            try:
                # Mock data for now - in production, this would fetch from data store
                # You would integrate with your existing data loading mechanisms
                import pandas as pd
                from datetime import datetime, timedelta
                
                # Generate sample data for demonstration
                now = datetime.now()
                data = []
                
                for i in range(bars):
                    timestamp = now - timedelta(minutes=bars-i)
                    # Mock OHLC data - replace with actual data loading
                    base_price = 895.0 + (i % 20) * 0.5
                    data.append({
                        "timestamp": timestamp.isoformat(),
                        "open": base_price,
                        "high": base_price + 2.0,
                        "low": base_price - 1.5,
                        "close": base_price + 1.0,
                        "volume": 1000 + (i % 100) * 10
                    })
                
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "bars": data,
                    "count": len(data)
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")

        @app.get("/api/chart/indicators")
        async def get_chart_indicators(strategy: str = "sma_fractal_scalper", timeframe: str = "1m"):
            """Get indicator data for chart display."""
            try:
                # Mock indicator data - replace with actual indicator calculations
                from datetime import datetime, timedelta
                
                now = datetime.now()
                indicators = {
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "sma_5": [],
                    "sma_200": [],
                    "fractals": [],
                    "signals": []
                }
                
                # Generate sample SMA data
                for i in range(200):
                    timestamp = now - timedelta(minutes=200-i)
                    
                    # 5-SMA data
                    indicators["sma_5"].append({
                        "timestamp": timestamp.isoformat(),
                        "value": 895.0 + (i % 10) * 0.3
                    })
                    
                    # 200-SMA data (slower moving)
                    indicators["sma_200"].append({
                        "timestamp": timestamp.isoformat(),
                        "value": 894.0 + (i % 50) * 0.1
                    })
                
                # Generate sample fractal data
                for i in range(0, 200, 20):
                    timestamp = now - timedelta(minutes=200-i)
                    
                    # High fractal
                    indicators["fractals"].append({
                        "timestamp": timestamp.isoformat(),
                        "type": "high",
                        "price": 897.0 + (i % 30) * 0.2
                    })
                    
                    # Low fractal
                    if i > 10:
                        indicators["fractals"].append({
                            "timestamp": (timestamp - timedelta(minutes=10)).isoformat(),
                            "type": "low",
                            "price": 893.0 + (i % 25) * 0.15
                        })
                
                return indicators
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch indicator data: {str(e)}")

        @app.websocket("/ws/chart")
        async def chart_websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time chart updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                # Send initial connection confirmation
                await websocket.send_json({
                    "type": "connection",
                    "data": {"status": "connected"},
                    "timestamp": datetime.now().isoformat()
                })
                
                while True:
                    # Send mock real-time updates
                    # In production, this would be triggered by actual market data
                    import random
                    
                    # Mock bar update
                    bar_update = {
                        "type": "bar_update",
                        "data": {
                            "symbol": "GOLDGUINEA",
                            "timeframe": "1m",
                            "bar": {
                                "timestamp": datetime.now().isoformat(),
                                "open": 895.0 + random.uniform(-2, 2),
                                "high": 897.0 + random.uniform(-1, 3),
                                "low": 893.0 + random.uniform(-3, 1),
                                "close": 895.5 + random.uniform(-2, 2),
                                "volume": 1000 + random.randint(0, 500)
                            }
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await websocket.send_json(bar_update)
                    await asyncio.sleep(10)  # Update every 10 seconds for demo
                    
            except WebSocketDisconnect:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
            except Exception as e:
                self.logger.error(f"Chart WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)

        @app.get("/chart")
        async def chart_dashboard():
            """Serve the advanced chart dashboard."""
            # Get absolute path from project root
            project_root = Path(__file__).parent.parent.parent
            chart_html_path = project_root / "web_dashboard" / "templates" / "chart.html"
            
            if chart_html_path.exists():
                return FileResponse(str(chart_html_path))
            else:
                raise HTTPException(status_code=404, detail=f"Chart dashboard not found at {chart_html_path}")

        # Mount static files for the chart dashboard
        try:
            project_root = Path(__file__).parent.parent.parent
            static_dir = project_root / "web_dashboard" / "static"
            if static_dir.exists():
                app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
            else:
                self.logger.warning(f"Static directory not found at {static_dir}")
        except Exception as e:
            self.logger.warning(f"Could not mount static files: {e}")

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)

            try:
                while True:
                    # Send periodic updates
                    status = await get_status()
                    await websocket.send_json(status)
                    await asyncio.sleep(5)  # Update every 5 seconds

            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)

    async def _start_daemon_background(self, daemon: PaperTradingDaemon):
        """Start daemon in background."""
        try:
            daemon.daemonize()
            await daemon.initialize()
            await daemon.start()
        except Exception as e:
            self.logger.error(f"Error starting daemon: {e}")

    def _generate_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Paper Trading Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .controls {
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover { background: #0056b3; }
        .btn.danger { background: #dc3545; }
        .btn.danger:hover { background: #c82333; }
        .btn.success { background: #28a745; }
        .btn.success:hover { background: #218838; }
        .status {
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .status-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }
        .status-card h3 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .status-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
        .logs {
            padding: 20px;
            border-top: 1px solid #eee;
        }
        .log-container {
            background: #1e1e1e;
            color: #fff;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #28a745; }
        .status-stopped { background: #dc3545; }
        .status-unknown { background: #ffc107; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Paper Trading Dashboard</h1>
            <p>Real-time monitoring and control</p>
        </div>
        
        <div class="controls">
            <button class="btn success" onclick="startDaemon()">▶️ Start</button>
            <button class="btn danger" onclick="stopDaemon()">⏹️ Stop</button>
            <button class="btn" onclick="restartDaemon()">🔄 Restart</button>
            <button class="btn" onclick="healthCheck()">❤️ Health Check</button>
            <button class="btn" onclick="refreshStatus()">🔄 Refresh</button>
        </div>
        
        <div class="status" id="status">
            <div class="status-card">
                <h3><span class="status-indicator status-unknown"></span>Daemon Status</h3>
                <div class="status-value" id="daemon-status">Unknown</div>
            </div>
            <div class="status-card">
                <h3>📊 Total P&L</h3>
                <div class="status-value" id="total-pnl">-</div>
            </div>
            <div class="status-card">
                <h3>📍 Open Positions</h3>
                <div class="status-value" id="open-positions">-</div>
            </div>
            <div class="status-card">
                <h3>⏱️ Uptime</h3>
                <div class="status-value" id="uptime">-</div>
            </div>
            <div class="status-card">
                <h3>💰 Current Price</h3>
                <div class="status-value" id="current-price">-</div>
            </div>
            <div class="status-card">
                <h3>📈 SMA Trend</h3>
                <div class="status-value" id="sma-trend">-</div>
            </div>
            <div class="status-card">
                <h3>🎯 Total Signals</h3>
                <div class="status-value" id="signal-count">-</div>
            </div>
            <div class="status-card">
                <h3>📊 Executed Trades</h3>
                <div class="status-value" id="total-trades">-</div>
            </div>
            <div class="status-card">
                <h3>📋 Total Orders</h3>
                <div class="status-value" id="total-orders">-</div>
            </div>
            <div class="status-card">
                <h3>🔔 Last Signal</h3>
                <div class="status-value" id="last-signal">-</div>
            </div>
        </div>
        
        <div class="status" style="margin-top: 20px;">
            <div class="status-card">
                <h3>📊 5-SMA</h3>
                <div class="status-value" id="sma-short">-</div>
            </div>
            <div class="status-card">
                <h3>📊 200-SMA</h3>
                <div class="status-value" id="sma-long">-</div>
            </div>
            <div class="status-card">
                <h3>🔍 Fractal Status</h3>
                <div class="status-value" id="fractal-status">-</div>
            </div>
            <div class="status-card">
                <h3>❌ No Signal Reason</h3>
                <div class="status-value" id="no-signal-reason" style="font-size: 14px;">-</div>
            </div>
        </div>
        
        <div class="logs">
            <h3>📜 Recent Logs</h3>
            <div class="log-container" id="logs">
                Loading logs...
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateStatus(data);
            };
            
            ws.onclose = function() {
                setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
            };
        }
        
        function updateStatus(data) {
            const statusEl = document.getElementById('daemon-status');
            const statusIndicator = document.querySelector('.status-indicator');
            
            if (data.running) {
                statusEl.textContent = data.status || 'Running';
                statusIndicator.className = 'status-indicator status-running';
            } else {
                statusEl.textContent = 'Stopped';
                statusIndicator.className = 'status-indicator status-stopped';
            }
            
            document.getElementById('uptime').textContent = data.uptime || '-';
            
            // Update performance metrics if available
            if (data.health_stats) {
                document.getElementById('total-pnl').textContent = 
                    data.health_stats.total_pnl ? `₹${data.health_stats.total_pnl.toFixed(2)}` : '-';
                document.getElementById('open-positions').textContent = 
                    data.health_stats.open_positions || '-';
            }
        }
        
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {'Content-Type': 'application/json'}
                };
                if (data) options.body = JSON.stringify(data);
                
                const response = await fetch(`/api/${endpoint}`, options);
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.detail || 'API call failed');
                }
                
                return result;
            } catch (error) {
                alert(`Error: ${error.message}`);
                throw error;
            }
        }
        
        async function startDaemon() {
            await apiCall('start', 'POST');
            setTimeout(refreshStatus, 2000);
        }
        
        async function stopDaemon() {
            await apiCall('stop', 'POST');
            setTimeout(refreshStatus, 2000);
        }
        
        async function restartDaemon() {
            await apiCall('restart', 'POST');
            setTimeout(refreshStatus, 5000);
        }
        
        async function healthCheck() {
            await apiCall('health');
        }
        
        async function refreshStatus() {
            try {
                const status = await apiCall('status');
                updateStatus(status);
                
                // Also fetch and update indicators
                const indicators = await apiCall('indicators');
                updateIndicators(indicators);
            } catch (error) {
                console.error('Error refreshing status:', error);
            }
        }
        
        function updateIndicators(data) {
            // Update price and trend
            document.getElementById('current-price').textContent = 
                data.current_price ? `₹${data.current_price.toFixed(2)}` : '-';
            
            const trendEl = document.getElementById('sma-trend');
            trendEl.textContent = data.sma_trend || '-';
            
            // Color code the trend
            if (data.sma_trend === 'BULLISH') {
                trendEl.style.color = '#28a745';
            } else if (data.sma_trend === 'BEARISH') {
                trendEl.style.color = '#dc3545';
            } else {
                trendEl.style.color = '#007bff';
            }
            
            // Update SMA values
            document.getElementById('sma-short').textContent = 
                data.sma_short ? `₹${data.sma_short.toFixed(2)}` : '-';
            document.getElementById('sma-long').textContent = 
                data.sma_long ? `₹${data.sma_long.toFixed(2)}` : '-';
            
            // Update signal information
            document.getElementById('signal-count').textContent = data.signal_count || '0';
            document.getElementById('total-trades').textContent = data.total_trades || '0';
            document.getElementById('total-orders').textContent = data.total_orders || '0';
            document.getElementById('last-signal').textContent = data.last_signal || 'None';
            
            // Update fractal status
            const fractalEl = document.getElementById('fractal-status');
            fractalEl.textContent = data.fractal_status || 'Unknown';
            
            // Color code fractal status
            if (data.fractal_status === 'LONG_WAITING') {
                fractalEl.style.color = '#28a745';
            } else if (data.fractal_status === 'SHORT_WAITING') {
                fractalEl.style.color = '#dc3545';
            } else {
                fractalEl.style.color = '#007bff';
            }
            
            // Update no-signal reason (truncate if too long)
            const reason = data.no_signal_reason || '-';
            const truncatedReason = reason.length > 50 ? reason.substring(0, 50) + '...' : reason;
            document.getElementById('no-signal-reason').textContent = truncatedReason;
            document.getElementById('no-signal-reason').title = reason; // Full text on hover
        }
        
        async function loadLogs() {
            try {
                const result = await apiCall('logs?lines=50');
                const logsEl = document.getElementById('logs');
                
                // Format logs with proper line breaks and styling
                const formattedLogs = result.logs.map(log => {
                    // Add different colors for different log types
                    if (log.includes('ERROR')) {
                        return `<div style="color: #ff6b6b;">${log}</div>`;
                    } else if (log.includes('WARNING')) {
                        return `<div style="color: #feca57;">${log}</div>`;
                    } else if (log.includes('INFO')) {
                        return `<div style="color: #48dbfb;">${log}</div>`;
                    } else if (log.includes('Session Activity Summary')) {
                        return `<div style="color: #1dd1a1; font-weight: bold;">${log}</div>`;
                    } else if (log.includes('Total Trades:') || log.includes('Total P&L:') || log.includes('Broker')) {
                        return `<div style="color: #ffeaa7; margin-left: 20px;">${log}</div>`;
                    } else {
                        return `<div style="color: #ddd;">${log}</div>`;
                    }
                }).join('');
                
                logsEl.innerHTML = formattedLogs;
                logsEl.scrollTop = logsEl.scrollHeight;
            } catch (error) {
                console.error('Error loading logs:', error);
            }
        }
        
        // Initialize
        connectWebSocket();
        refreshStatus();
        loadLogs();
        
        // Refresh logs every 30 seconds
        setInterval(loadLogs, 30000);
    </script>
</body>
</html>
        """

    def run(self, host: str = "0.0.0.0", port: int = 8000, *, log_level: str = "info"):
        """Run the server with specified Uvicorn log-level."""
        self.logger.info(
            "Starting Paper Trading Server on %s:%s (log-level=%s)",
            host,
            port,
            log_level,
        )
        uvicorn.run(self.app, host=host, port=port, log_level=log_level)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument(
        "--config", default="config/paper_trading.yaml", help="Config file"
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level",
    )

    args = parser.parse_args()

    server = PaperTradingServer(args.config, log_level=args.log_level)
    server.run(host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
