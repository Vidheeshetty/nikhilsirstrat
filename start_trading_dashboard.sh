#!/bin/bash

# Trading Dashboard Startup Script
# Starts the paper trading server with chart dashboard
# Default: Uses V2 strategy with pluggable architecture

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - DEFAULT TO V2 STRATEGY
CONFIG_FILE="${1:-config/paper_trading/sma_scalper_v2.yaml}"
HOST="0.0.0.0"
PORT="8000"
LOG_LEVEL="info"

echo -e "${BLUE}🚀 Trading Dashboard Startup (V2 Strategy)${NC}"
echo -e "${BLUE}===========================================${NC}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Available configs:${NC}"
    ls -la config/paper_trading/
    exit 1
fi

# Check if required directories exist
if [ ! -d "web_dashboard" ]; then
    echo -e "${RED}❌ Web dashboard directory not found${NC}"
    exit 1
fi

# Check if Python dependencies are installed
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo -e "${RED}❌ Missing dependencies. Install with:${NC}"
    echo -e "${YELLOW}pip install fastapi uvicorn websockets${NC}"
    exit 1
}

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}⚠️  Port $PORT is already in use${NC}"
    echo -e "${YELLOW}Attempting to stop existing server...${NC}"
    pkill -f paper_trading_server || true
    sleep 2
fi

# Create necessary directories
mkdir -p runlogs/papertrading
mkdir -p web_dashboard/static/libs

# Check if TradingView charts library exists
if [ ! -f "web_dashboard/static/libs/lightweight-charts.standalone.production.js" ]; then
    echo -e "${YELLOW}📦 Downloading TradingView Lightweight Charts...${NC}"
    curl -o web_dashboard/static/libs/lightweight-charts.standalone.production.js \
         https://cdn.jsdelivr.net/npm/lightweight-charts/dist/lightweight-charts.standalone.production.js
fi

echo -e "${GREEN}✅ All checks passed${NC}"
echo ""

# Start the server
echo -e "${BLUE}🚀 Starting Trading Dashboard Server...${NC}"
echo -e "${YELLOW}Configuration: $CONFIG_FILE${NC}"
echo -e "${YELLOW}Server URL: http://$HOST:$PORT${NC}"
echo -e "${YELLOW}Dashboard URL: http://$HOST:$PORT/chart${NC}"
echo ""

# Start server in foreground
python3 scripts/paper_trading/paper_trading_server.py \
    --config "$CONFIG_FILE" \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LOG_LEVEL" 