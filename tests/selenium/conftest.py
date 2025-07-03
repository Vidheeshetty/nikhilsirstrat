"""
Pytest configuration and fixtures for selenium-based UI testing.

Provides shared fixtures for:
- Browser setup and teardown
- Paper trading server management
- Test data generation
- Screenshot capture on failures
- Performance monitoring
"""

import pytest
import asyncio
import subprocess
import time
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Generator
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Test configuration
TEST_CONFIG = {
    "paper_trading_config": "config/paper_trading/my_zerodha.yaml",
    "dashboard_url": "http://localhost:8000",
    "paper_trading_server_url": "http://localhost:5000",
    "screenshot_dir": "testlogs/screenshots",
    "test_data_dir": "tests/data",
    "browser_timeout": 30,
    "server_startup_timeout": 15,
}

@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG

@pytest.fixture(scope="session")
def screenshot_dir():
    """Ensure screenshot directory exists."""
    screenshot_path = Path(TEST_CONFIG["screenshot_dir"])
    screenshot_path.mkdir(parents=True, exist_ok=True)
    return screenshot_path

@pytest.fixture(scope="session")
def paper_trading_server():
    """Start paper trading server for testing."""
    print("Starting paper trading server...")
    
    # Start the paper trading server
    process = subprocess.Popen([
        "python3", "scripts/paper_trading/paper_trading_server.py",
        "--config", TEST_CONFIG["paper_trading_config"]
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(TEST_CONFIG["server_startup_timeout"])
    
    # Verify server is running
    try:
        import requests
        response = requests.get(f"{TEST_CONFIG['paper_trading_server_url']}/health", timeout=5)
        assert response.status_code == 200
        print("Paper trading server started successfully")
    except Exception as e:
        process.terminate()
        raise RuntimeError(f"Paper trading server failed to start: {e}")
    
    yield process
    
    # Cleanup
    print("Stopping paper trading server...")
    process.terminate()
    process.wait()

@pytest.fixture(scope="session")
def chrome_options():
    """Configure Chrome browser options for testing."""
    options = Options()
    options.add_argument("--headless")  # Run in headless mode for CI/CD
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")  # Faster loading
    return options

@pytest.fixture(scope="function")
def browser(chrome_options, screenshot_dir):
    """Create and configure Chrome browser instance."""
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(TEST_CONFIG["browser_timeout"])
    
    yield driver
    
    # Capture screenshot on test failure
    if hasattr(pytest, "current_test_failed") and pytest.current_test_failed:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshot_dir / f"failure_{timestamp}.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"Screenshot saved: {screenshot_path}")
    
    driver.quit()

@pytest.fixture(scope="function")
def dashboard_page(browser, paper_trading_server):
    """Navigate to dashboard page and wait for it to load."""
    browser.get(TEST_CONFIG["dashboard_url"])
    
    # Wait for dashboard to load
    WebDriverWait(browser, TEST_CONFIG["browser_timeout"]).until(
        EC.presence_of_element_located((By.ID, "trading-dashboard"))
    )
    
    return browser

@pytest.fixture(scope="function")
def sample_market_data():
    """Generate sample market data for testing."""
    return {
        "bars": [
            {"timestamp": "2025-07-02T09:15:00", "open": 890.50, "high": 891.20, "low": 889.80, "close": 890.90, "volume": 15000},
            {"timestamp": "2025-07-02T09:16:00", "open": 890.90, "high": 892.10, "low": 890.30, "close": 891.50, "volume": 18000},
            {"timestamp": "2025-07-02T09:17:00", "open": 891.50, "high": 893.00, "low": 891.00, "close": 892.75, "volume": 22000},
            {"timestamp": "2025-07-02T09:18:00", "open": 892.75, "high": 894.50, "low": 892.20, "close": 893.80, "volume": 25000},
            {"timestamp": "2025-07-02T09:19:00", "open": 893.80, "high": 895.20, "low": 893.50, "close": 894.60, "volume": 20000},
        ],
        "signals": [
            {"timestamp": "2025-07-02T09:17:00", "type": "LONG", "price": 892.75, "stop_loss": 890.50},
            {"timestamp": "2025-07-02T09:19:00", "type": "SHORT", "price": 894.60, "stop_loss": 896.00},
        ],
        "indicators": {
            "sma_short": [890.70, 891.20, 891.85, 892.40, 893.12],
            "sma_long": [889.50, 889.55, 889.62, 889.70, 889.78],
            "fractals": {
                "highs": [{"timestamp": "2025-07-02T09:18:00", "price": 894.50}],
                "lows": [{"timestamp": "2025-07-02T09:15:00", "price": 889.80}]
            }
        }
    }

@pytest.fixture(scope="function")
def performance_monitor():
    """Monitor performance metrics during tests."""
    start_time = time.time()
    metrics = {"start_time": start_time}
    
    yield metrics
    
    end_time = time.time()
    metrics["end_time"] = end_time
    metrics["duration"] = end_time - start_time
    
    # Log performance metrics
    print(f"Test duration: {metrics['duration']:.2f} seconds")

# Hook to capture test failures for screenshot functionality
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture test failure status for screenshot functionality."""
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        pytest.current_test_failed = True
    else:
        pytest.current_test_failed = False

# Custom markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "dev: Development phase tests (temporary)")
    config.addinivalue_line("markers", "prod: Production tests (permanent)")
    config.addinivalue_line("markers", "debug: Debug and exploration tests")
    config.addinivalue_line("markers", "selenium: Browser automation tests")
    config.addinivalue_line("markers", "chart: Chart functionality tests")
    config.addinivalue_line("markers", "realtime: Real-time data tests")
    config.addinivalue_line("markers", "performance: Performance benchmark tests") 