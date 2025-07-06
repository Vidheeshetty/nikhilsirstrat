#!/bin/bash

# Paper Trading Startup Script
# Starts both the daemon and web server for paper trading
# Default: Uses V2 strategy with pluggable architecture

set -e

CONFIG_FILE="${1:-config/paper_trading/sma_scalper_v2.yaml}"
DAEMON_CMD="python3 scripts/paper_trading/run_paper_trading_daemon.py --config $CONFIG_FILE"
WEB_SERVER_CMD="python3 scripts/paper_trading/paper_trading_server.py --config $CONFIG_FILE --host 0.0.0.0 --port 8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to start daemon
start_daemon() {
    print_status "Starting Paper Trading Daemon..."
    
    # Check if daemon is already running
    if pgrep -f "run_paper_trading_daemon.py" > /dev/null; then
        print_warning "Paper Trading Daemon is already running"
        return 0
    fi
    
    # Start daemon in background
    nohup $DAEMON_CMD > runlogs/papertrading/daemon_console.log 2>&1 &
    DAEMON_PID=$!
    
    # Wait a bit and check if it's still running
    sleep 3
    if kill -0 $DAEMON_PID 2>/dev/null; then
        print_success "Paper Trading Daemon started (PID: $DAEMON_PID)"
        echo $DAEMON_PID > runlogs/papertrading/daemon.pid
    else
        print_error "Failed to start Paper Trading Daemon"
        return 1
    fi
}

# Function to start web server
start_web_server() {
    print_status "Starting Paper Trading Web Server..."
    
    # Check if web server is already running
    if check_port 8000; then
        print_warning "Web server is already running on port 8000"
        return 0
    fi
    
    # Start web server in background
    nohup $WEB_SERVER_CMD > runlogs/papertrading/web_server.log 2>&1 &
    WEB_PID=$!
    
    # Wait a bit and check if it's still running
    sleep 3
    if kill -0 $WEB_PID 2>/dev/null; then
        print_success "Paper Trading Web Server started (PID: $WEB_PID)"
        echo $WEB_PID > runlogs/papertrading/web_server.pid
    else
        print_error "Failed to start Paper Trading Web Server"
        return 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping Paper Trading services..."
    
    # Stop daemon
    if [ -f runlogs/papertrading/daemon.pid ]; then
        DAEMON_PID=$(cat runlogs/papertrading/daemon.pid)
        if kill -0 $DAEMON_PID 2>/dev/null; then
            kill $DAEMON_PID
            print_success "Paper Trading Daemon stopped"
        fi
        rm -f runlogs/papertrading/daemon.pid
    fi
    
    # Stop web server
    if [ -f runlogs/papertrading/web_server.pid ]; then
        WEB_PID=$(cat runlogs/papertrading/web_server.pid)
        if kill -0 $WEB_PID 2>/dev/null; then
            kill $WEB_PID
            print_success "Paper Trading Web Server stopped"
        fi
        rm -f runlogs/papertrading/web_server.pid
    fi
    
    # Also kill any remaining processes
    pkill -f "run_paper_trading_daemon.py" 2>/dev/null || true
    pkill -f "paper_trading_server.py" 2>/dev/null || true
}

# Function to show status
show_status() {
    print_status "Paper Trading Service Status:"
    echo
    
    # Check daemon
    if pgrep -f "run_paper_trading_daemon.py" > /dev/null; then
        print_success "✅ Paper Trading Daemon: RUNNING"
    else
        print_error "❌ Paper Trading Daemon: STOPPED"
    fi
    
    # Check web server
    if check_port 8000; then
        print_success "✅ Web Server: RUNNING (http://localhost:8000)"
    else
        print_error "❌ Web Server: STOPPED"
    fi
    
    echo
    print_status "Recent log entries:"
    if [ -f runlogs/papertrading/daemon_console.log ]; then
        echo "--- Daemon Logs (last 5 lines) ---"
        tail -5 runlogs/papertrading/daemon_console.log
    fi
    
    if [ -f runlogs/papertrading/web_server.log ]; then
        echo "--- Web Server Logs (last 5 lines) ---"
        tail -5 runlogs/papertrading/web_server.log
    fi
}

# Main script logic
case "${1:-start}" in
    start)
        print_status "Starting Paper Trading Platform..."
        
        # Create log directory
        mkdir -p runlogs/papertrading
        
        # Start services
        start_daemon
        start_web_server
        
        echo
        print_success "🚀 Paper Trading Platform (V2 Strategy) Started Successfully!"
        echo
        echo "📊 Web Dashboard: http://localhost:8000"
        echo "🔧 Strategy: SmaFractalScalperV2 (Pluggable Architecture)"
        echo "📋 Logs Directory: runlogs/papertrading/"
        echo
        echo "Use './start_paper_trading.sh status' to check service status"
        echo "Use './start_paper_trading.sh stop' to stop all services"
        ;;
        
    stop)
        stop_services
        print_success "Paper Trading Platform stopped"
        ;;
        
    restart)
        print_status "Restarting Paper Trading Platform..."
        stop_services
        sleep 2
        start_daemon
        start_web_server
        print_success "Paper Trading Platform restarted"
        ;;
        
    status)
        show_status
        ;;
        
    logs)
        print_status "Showing live logs (Ctrl+C to exit)..."
        if [ -f runlogs/papertrading/daemon_console.log ]; then
            tail -f runlogs/papertrading/daemon_console.log
        else
            print_error "No daemon logs found"
        fi
        ;;
        
    web-logs)
        print_status "Showing web server logs (Ctrl+C to exit)..."
        if [ -f runlogs/papertrading/web_server.log ]; then
            tail -f runlogs/papertrading/web_server.log
        else
            print_error "No web server logs found"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|web-logs}"
        echo
        echo "Commands:"
        echo "  start     - Start both daemon and web server"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show service status"
        echo "  logs      - Show live daemon logs"
        echo "  web-logs  - Show live web server logs"
        exit 1
        ;;
esac 