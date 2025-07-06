#!/bin/bash

# TradingView Integration Test Runner
# Comprehensive testing script for TradingView Lightweight Charts integration

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/tests/selenium"
RESULTS_DIR="$PROJECT_ROOT/testlogs"
SCREENSHOTS_DIR="$RESULTS_DIR/screenshots"
REPORTS_DIR="$RESULTS_DIR/reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Setup directories
setup_test_environment() {
    log_info "Setting up test environment..."
    
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$SCREENSHOTS_DIR"
    mkdir -p "$REPORTS_DIR"
    
    # Clean old screenshots
    find "$SCREENSHOTS_DIR" -name "*.png" -mtime +7 -delete 2>/dev/null || true
    
    log_success "Test environment ready"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required"
        exit 1
    fi
    
    # Check Chrome/Chromium
    if ! command -v google-chrome &> /dev/null && ! command -v chromium &> /dev/null; then
        log_warning "Chrome/Chromium not found - tests may fail"
    fi
    
    # Check pytest
    if ! python3 -c "import pytest" 2>/dev/null; then
        log_error "pytest is required. Install with: pip install -r requirements-selenium-testing.txt"
        exit 1
    fi
    
    # Check selenium
    if ! python3 -c "import selenium" 2>/dev/null; then
        log_error "Selenium is required. Install with: pip install -r requirements-selenium-testing.txt"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Start paper trading server
start_server() {
    log_info "Starting paper trading server..."
    
    # Check if server is already running
    if curl -s http://localhost:8000/api/status >/dev/null 2>&1; then
        log_warning "Server already running on port 8000"
        return 0
    fi
    
    # Start server in background
    cd "$PROJECT_ROOT"
    python3 scripts/paper_trading/paper_trading_server.py \
        --config config/paper_trading/my_zerodha.yaml \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info > "$RESULTS_DIR/server.log" 2>&1 &
    
    SERVER_PID=$!
    echo $SERVER_PID > "$RESULTS_DIR/server.pid"
    
    # Wait for server to start
    log_info "Waiting for server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/status >/dev/null 2>&1; then
            log_success "Server started successfully (PID: $SERVER_PID)"
            return 0
        fi
        sleep 1
    done
    
    log_error "Server failed to start within 30 seconds"
    return 1
}

# Stop paper trading server
stop_server() {
    if [ -f "$RESULTS_DIR/server.pid" ]; then
        SERVER_PID=$(cat "$RESULTS_DIR/server.pid")
        if kill -0 $SERVER_PID 2>/dev/null; then
            log_info "Stopping server (PID: $SERVER_PID)..."
            kill $SERVER_PID
            rm -f "$RESULTS_DIR/server.pid"
            log_success "Server stopped"
        fi
    fi
}

# Run specific test category
run_test_category() {
    local category=$1
    local description=$2
    
    log_info "Running $description tests..."
    
    cd "$PROJECT_ROOT"
    
    case $category in
        "api-fixes")
            pytest -v -m "dev" \
                tests/selenium/test_suites/test_tradingview_fixes.py::TestTradingViewAPIFixes \
                --html="$REPORTS_DIR/api_fixes_report.html" \
                --tb=short
            ;;
        "debugging")
            pytest -v -m "debug" \
                tests/selenium/test_suites/test_tradingview_fixes.py::TestTradingViewDebugging \
                --html="$REPORTS_DIR/debugging_report.html" \
                --tb=long -s
            ;;
        "performance")
            pytest -v -m "performance" \
                tests/selenium/test_suites/test_tradingview_fixes.py::TestTradingViewPerformance \
                --html="$REPORTS_DIR/performance_report.html" \
                --tb=short
            ;;
        "chart-rendering")
            pytest -v -m "chart" \
                tests/selenium/test_suites/test_chart_rendering.py \
                --html="$REPORTS_DIR/chart_rendering_report.html" \
                --tb=short
            ;;
        "dashboard-integration")
            pytest -v -m "prod" \
                tests/selenium/test_suites/test_dashboard_integration.py \
                --html="$REPORTS_DIR/dashboard_integration_report.html" \
                --tb=short
            ;;
        "all")
            pytest -v \
                tests/selenium/test_suites/ \
                --html="$REPORTS_DIR/full_test_report.html" \
                --tb=short
            ;;
        *)
            log_error "Unknown test category: $category"
            return 1
            ;;
    esac
}

# Generate summary report
generate_summary() {
    log_info "Generating test summary..."
    
    SUMMARY_FILE="$RESULTS_DIR/test_summary.txt"
    
    cat > "$SUMMARY_FILE" << EOF
TradingView Integration Test Summary
===================================
Date: $(date)
Project: NTbasedPlatform
Framework: Selenium WebDriver + pytest

Test Results:
EOF
    
    # Count test results from reports
    if [ -d "$REPORTS_DIR" ]; then
        for report in "$REPORTS_DIR"/*.html; do
            if [ -f "$report" ]; then
                echo "- $(basename "$report")" >> "$SUMMARY_FILE"
            fi
        done
    fi
    
    echo "" >> "$SUMMARY_FILE"
    echo "Screenshots: $(ls "$SCREENSHOTS_DIR"/*.png 2>/dev/null | wc -l) captured" >> "$SUMMARY_FILE"
    echo "Server Log: $RESULTS_DIR/server.log" >> "$SUMMARY_FILE"
    
    log_success "Summary generated: $SUMMARY_FILE"
}

# Main execution
main() {
    echo "========================================"
    echo "TradingView Integration Test Runner"
    echo "========================================"
    
    # Parse arguments
    TEST_CATEGORY=${1:-"api-fixes"}
    
    case $TEST_CATEGORY in
        "help"|"-h"|"--help")
            echo "Usage: $0 [test-category]"
            echo ""
            echo "Test Categories:"
            echo "  api-fixes           - TradingView API compatibility tests"
            echo "  debugging           - Debug and error analysis tests"
            echo "  performance         - Performance benchmark tests"
            echo "  chart-rendering     - Chart rendering functionality tests"
            echo "  dashboard-integration - Full dashboard integration tests"
            echo "  all                 - Run all test suites"
            echo ""
            echo "Examples:"
            echo "  $0 api-fixes        # Test API fixes only"
            echo "  $0 debugging        # Run debug tests with detailed output"
            echo "  $0 all              # Run complete test suite"
            exit 0
            ;;
    esac
    
    # Setup and checks
    setup_test_environment
    check_prerequisites
    
    # Start server
    if ! start_server; then
        log_error "Failed to start server"
        exit 1
    fi
    
    # Setup cleanup trap
    trap 'stop_server' EXIT
    
    # Run tests
    case $TEST_CATEGORY in
        "api-fixes")
            run_test_category "api-fixes" "TradingView API Fixes"
            ;;
        "debugging")
            run_test_category "debugging" "Debug Analysis"
            ;;
        "performance")
            run_test_category "performance" "Performance Benchmark"
            ;;
        "chart-rendering")
            run_test_category "chart-rendering" "Chart Rendering"
            ;;
        "dashboard-integration")
            run_test_category "dashboard-integration" "Dashboard Integration"
            ;;
        "all")
            log_info "Running complete test suite..."
            run_test_category "api-fixes" "TradingView API Fixes"
            run_test_category "debugging" "Debug Analysis"
            run_test_category "performance" "Performance Benchmark"
            run_test_category "chart-rendering" "Chart Rendering"
            run_test_category "dashboard-integration" "Dashboard Integration"
            ;;
        *)
            log_error "Unknown test category: $TEST_CATEGORY"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    # Generate summary
    generate_summary
    
    log_success "Testing complete! Check reports in: $REPORTS_DIR"
    echo ""
    echo "Quick Links:"
    echo "- Test Reports: $REPORTS_DIR/"
    echo "- Screenshots: $SCREENSHOTS_DIR/"
    echo "- Server Log: $RESULTS_DIR/server.log"
    echo "- Summary: $RESULTS_DIR/test_summary.txt"
}

# Execute main function
main "$@" 