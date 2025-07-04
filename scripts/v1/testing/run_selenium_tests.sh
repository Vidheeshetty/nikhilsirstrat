#!/bin/bash

# Selenium Test Runner Script
# Usage: ./scripts/testing/run_selenium_tests.sh [test_type] [options]

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/tests/selenium"
LOG_DIR="$PROJECT_ROOT/testlogs"
VENV_DIR="$PROJECT_ROOT/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [test_type] [options]"
    echo ""
    echo "Test Types:"
    echo "  dev        - Run development tests (temporary, detailed)"
    echo "  prod       - Run production tests (permanent, core functionality)"
    echo "  debug      - Run debug tests (troubleshooting, state capture)"
    echo "  all        - Run all tests"
    echo "  chart      - Run chart-specific tests only"
    echo "  performance - Run performance benchmark tests"
    echo ""
    echo "Options:"
    echo "  --headless     - Run in headless mode (default for CI)"
    echo "  --headed       - Run with visible browser"
    echo "  --parallel     - Run tests in parallel"
    echo "  --coverage     - Generate coverage report"
    echo "  --html-report  - Generate HTML test report"
    echo "  --verbose      - Verbose output"
    echo "  --help         - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev --headed --verbose"
    echo "  $0 prod --headless --parallel"
    echo "  $0 chart --coverage"
    echo "  $0 debug --html-report"
}

# Function to check prerequisites
check_prerequisites() {
    print_color $BLUE "Checking prerequisites..."
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        print_color $RED "Virtual environment not found at $VENV_DIR"
        print_color $YELLOW "Please create virtual environment first: python3 -m venv venv"
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Check if selenium requirements are installed
    if ! python -c "import selenium" 2>/dev/null; then
        print_color $YELLOW "Installing selenium testing requirements..."
        pip install -r "$PROJECT_ROOT/requirements-selenium-testing.txt"
    fi
    
    # Check if Chrome/Chromium is available
    if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null; then
        print_color $RED "Chrome or Chromium browser not found"
        print_color $YELLOW "Please install Chrome or Chromium browser"
        exit 1
    fi
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    mkdir -p "$LOG_DIR/screenshots"
    mkdir -p "$LOG_DIR/debug"
    
    print_color $GREEN "Prerequisites check passed"
}

# Function to start required services
start_services() {
    print_color $BLUE "Starting required services..."
    
    # Check if paper trading server is running
    if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
        print_color $YELLOW "Starting paper trading server..."
        cd "$PROJECT_ROOT"
        python3 scripts/paper_trading/paper_trading_server.py --config config/paper_trading/my_zerodha.yaml &
        SERVER_PID=$!
        
        # Wait for server to start
        sleep 10
        
        # Verify server started
        if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
            print_color $RED "Failed to start paper trading server"
            exit 1
        fi
        
        print_color $GREEN "Paper trading server started (PID: $SERVER_PID)"
    else
        print_color $GREEN "Paper trading server already running"
    fi
    
    # Check if web dashboard is running
    if ! curl -s http://localhost:8000 > /dev/null 2>&1; then
        print_color $YELLOW "Web dashboard not running - tests may fail"
        print_color $YELLOW "Start dashboard with: ./start_trading_dashboard.sh"
    else
        print_color $GREEN "Web dashboard is running"
    fi
}

# Function to stop services
stop_services() {
    print_color $BLUE "Stopping services..."
    
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        print_color $GREEN "Stopped paper trading server"
    fi
}

# Function to run tests
run_tests() {
    local test_type="$1"
    shift
    local pytest_args=()
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --headless)
                export SELENIUM_HEADLESS=true
                shift
                ;;
            --headed)
                export SELENIUM_HEADLESS=false
                shift
                ;;
            --parallel)
                pytest_args+=("-n" "auto")
                shift
                ;;
            --coverage)
                pytest_args+=("--cov=src" "--cov-report=html:$LOG_DIR/coverage")
                shift
                ;;
            --html-report)
                pytest_args+=("--html=$LOG_DIR/selenium_report.html" "--self-contained-html")
                shift
                ;;
            --verbose)
                pytest_args+=("-v" "-s")
                shift
                ;;
            *)
                print_color $RED "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Set default to headless if not specified
    if [ -z "$SELENIUM_HEADLESS" ]; then
        export SELENIUM_HEADLESS=true
    fi
    
    # Build pytest command based on test type
    case $test_type in
        dev)
            pytest_args+=("-m" "dev")
            print_color $BLUE "Running development tests..."
            ;;
        prod)
            pytest_args+=("-m" "prod")
            print_color $BLUE "Running production tests..."
            ;;
        debug)
            pytest_args+=("-m" "debug")
            print_color $BLUE "Running debug tests..."
            ;;
        chart)
            pytest_args+=("-m" "chart")
            print_color $BLUE "Running chart tests..."
            ;;
        performance)
            pytest_args+=("-m" "performance")
            print_color $BLUE "Running performance tests..."
            ;;
        all)
            print_color $BLUE "Running all selenium tests..."
            ;;
        *)
            print_color $RED "Invalid test type: $test_type"
            show_usage
            exit 1
            ;;
    esac
    
    # Add selenium marker to all runs
    pytest_args+=("-m" "selenium")
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run pytest
    print_color $BLUE "Executing: pytest ${pytest_args[@]} $TEST_DIR"
    
    if pytest "${pytest_args[@]}" "$TEST_DIR"; then
        print_color $GREEN "Tests completed successfully!"
        return 0
    else
        print_color $RED "Tests failed!"
        return 1
    fi
}

# Function to generate test report
generate_report() {
    print_color $BLUE "Generating test summary..."
    
    if [ -f "$LOG_DIR/selenium_report.html" ]; then
        print_color $GREEN "HTML report available at: $LOG_DIR/selenium_report.html"
    fi
    
    if [ -f "$LOG_DIR/coverage/index.html" ]; then
        print_color $GREEN "Coverage report available at: $LOG_DIR/coverage/index.html"
    fi
    
    # Count screenshots (failures)
    screenshot_count=$(find "$LOG_DIR/screenshots" -name "*.png" 2>/dev/null | wc -l)
    if [ $screenshot_count -gt 0 ]; then
        print_color $YELLOW "Found $screenshot_count failure screenshots in $LOG_DIR/screenshots"
    fi
    
    # Count debug files
    debug_count=$(find "$LOG_DIR/debug" -name "*.json" 2>/dev/null | wc -l)
    if [ $debug_count -gt 0 ]; then
        print_color $BLUE "Found $debug_count debug state files in $LOG_DIR/debug"
    fi
}

# Main execution
main() {
    # Handle help
    if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ $# -eq 0 ]]; then
        show_usage
        exit 0
    fi
    
    local test_type="$1"
    shift
    
    print_color $BLUE "=== Selenium Test Runner ==="
    print_color $BLUE "Test type: $test_type"
    print_color $BLUE "Options: $@"
    print_color $BLUE "Headless: ${SELENIUM_HEADLESS:-true}"
    echo ""
    
    # Setup trap to cleanup on exit
    trap stop_services EXIT
    
    # Execute test pipeline
    check_prerequisites
    start_services
    
    if run_tests "$test_type" "$@"; then
        test_result=0
    else
        test_result=1
    fi
    
    generate_report
    
    print_color $BLUE "=== Test Execution Complete ==="
    exit $test_result
}

# Execute main function with all arguments
main "$@" 