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
            """Get recent log entries."""
            log_file = Path("runlogs/papertrading/paper_trading.log")
            if not log_file.exists():
                return {"logs": []}

            try:
                with open(log_file, "r") as f:
                    all_lines = f.readlines()
                    recent_lines = (
                        all_lines[-lines:] if len(all_lines) > lines else all_lines
                    )
                    return {"logs": [line.strip() for line in recent_lines]}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

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
            } catch (error) {
                console.error('Error refreshing status:', error);
            }
        }
        
        async function loadLogs() {
            try {
                const result = await apiCall('logs?lines=50');
                const logsEl = document.getElementById('logs');
                logsEl.innerHTML = result.logs.join('\\n');
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
