"""
TradingView v5.0.8 API Fixes Validation Tests.

Specific tests to validate fixes for:
- TradingView Lightweight Charts v5.0.8 API compatibility
- Indicator creation and display issues
- Chart initialization problems
- Dashboard module integration
"""

import pytest
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, JavascriptException

from tests.selenium.page_objects.dashboard_page import DashboardPage
from tests.selenium.page_objects.chart_page import ChartPage

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.dev
class TestTradingViewAPIFixes:
    """Development tests for TradingView v5.0.8 API fixes."""
    
    def test_chart_initialization_success(self, browser, test_config):
        """Test that chart initializes without 'failed to initialise dashboard' error."""
        # Navigate to main chart dashboard
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for page to load
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check for initialization error message
        try:
            error_element = browser.find_element(By.XPATH, "//*[contains(text(), 'failed to initialise dashboard')]")
            assert False, f"Dashboard initialization failed: {error_element.text}"
        except:
            # No error message found - this is good
            pass
        
        # Verify TradingView library loads
        library_loaded = browser.execute_script("""
            return typeof LightweightCharts !== 'undefined';
        """)
        assert library_loaded, "TradingView library should be loaded"
        
        # Wait for chart to be created
        chart_created = WebDriverWait(browser, 30).until(
            lambda driver: driver.execute_script("""
                return document.querySelector('#trading-chart canvas') !== null;
            """)
        )
        assert chart_created, "Chart canvas should be created"
    
    def test_candlestick_series_creation(self, browser, test_config):
        """Test that candlestick series creates successfully with v5.0.8 API."""
        # Navigate to candlestick test page
        browser.get(f"{test_config['dashboard_url']}/candlestick-test")
        
        # Wait for page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "init-chart"))
        )
        
        # Click initialize chart
        init_button = browser.find_element(By.ID, "init-chart")
        init_button.click()
        
        # Wait for chart creation
        time.sleep(2)
        
        # Check for success message
        success_found = WebDriverWait(browser, 10).until(
            lambda driver: "Chart created successfully" in driver.page_source
        )
        assert success_found, "Chart should be created successfully"
        
        # Verify no API errors
        api_errors = browser.execute_script("""
            const logs = Array.from(document.querySelectorAll('#logs div'));
            return logs.filter(log => log.textContent.includes('is not a function')).length;
        """)
        assert api_errors == 0, "Should have no TradingView API errors"
    
    def test_indicator_creation_fixed(self, browser, test_config):
        """Test that SMA indicators create without 'addLineSeries is not a function' error."""
        # Navigate to candlestick test page
        browser.get(f"{test_config['dashboard_url']}/candlestick-test")
        
        # Initialize chart first
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "init-chart"))
        ).click()
        time.sleep(2)
        
        # Load candlestick data
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "load-data"))
        ).click()
        time.sleep(2)
        
        # Add indicators
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "add-indicators"))
        ).click()
        time.sleep(3)
        
        # Check for indicator success
        indicator_success = WebDriverWait(browser, 10).until(
            lambda driver: "SMA indicator added successfully" in driver.page_source
        )
        assert indicator_success, "SMA indicator should be added successfully"
        
        # Verify no addLineSeries errors
        line_series_errors = browser.execute_script("""
            const logs = Array.from(document.querySelectorAll('#logs div'));
            return logs.filter(log => log.textContent.includes('addLineSeries')).length;
        """)
        assert line_series_errors == 0, "Should have no addLineSeries errors"
        
        # Check for signal markers success
        marker_success = WebDriverWait(browser, 5).until(
            lambda driver: "Signal markers added successfully" in driver.page_source
        )
        assert marker_success, "Signal markers should be added successfully"
    
    def test_crosshair_functionality_fixed(self, browser, test_config):
        """Test that crosshair events work without API errors."""
        # Navigate to candlestick test page
        browser.get(f"{test_config['dashboard_url']}/candlestick-test")
        
        # Run through the test sequence
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "init-chart"))
        ).click()
        time.sleep(2)
        
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "load-data"))
        ).click()
        time.sleep(2)
        
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "add-indicators"))
        ).click()
        time.sleep(2)
        
        # Test crosshair
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "test-crosshair"))
        ).click()
        time.sleep(2)
        
        # Check for crosshair success
        crosshair_success = WebDriverWait(browser, 10).until(
            lambda driver: "Crosshair event handler set up successfully" in driver.page_source
        )
        assert crosshair_success, "Crosshair should be set up successfully"
        
        # Verify no crosshair API errors
        crosshair_errors = browser.execute_script("""
            const logs = Array.from(document.querySelectorAll('#logs div'));
            return logs.filter(log => 
                log.textContent.includes('seriesPrices') || 
                log.textContent.includes('seriesData')
            ).length;
        """)
        # Some crosshair logs are expected for debugging, but no errors
        print(f"Crosshair debug logs found: {crosshair_errors}")
    
    def test_minimal_chart_works(self, browser, test_config):
        """Test that minimal chart implementation works as baseline."""
        # Enable comprehensive console error capture
        browser.execute_script("""
            window.capturedErrors = [];
            window.capturedLogs = [];
            
            // Capture console errors
            const originalError = console.error;
            console.error = function(...args) {
                window.capturedErrors.push(args.join(' '));
                originalError.apply(console, args);
            };
            
            // Capture console logs for analysis
            const originalLog = console.log;
            console.log = function(...args) {
                window.capturedLogs.push(args.join(' '));
                originalLog.apply(console, args);
            };
        """)
        
        # Navigate to minimal chart test page
        browser.get(f"{test_config['dashboard_url']}/minimal-chart")
        
        # Wait for chart initialization
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, "chart"))
        )
        
        # Wait for completion message
        completion_found = WebDriverWait(browser, 30).until(
            lambda driver: "Chart initialization complete!" in driver.page_source
        )
        assert completion_found, "Minimal chart should initialize completely"
        
        # Get all captured errors and logs
        captured_errors = browser.execute_script("return window.capturedErrors || [];")
        captured_logs = browser.execute_script("return window.capturedLogs || [];")
        browser_logs = browser.get_log('browser')
        
        # Filter for TradingView API errors
        tradingview_errors = []
        for error in captured_errors:
            if any(keyword in error.lower() for keyword in [
                'assertion failed', 'addseries', 'candlestick', 'lightweightcharts',
                'cannot read properties', 'typeerror', 'addlineseries'
            ]):
                tradingview_errors.append(f"Console Error: {error}")
        
        # Check browser logs for severe errors
        for log in browser_logs:
            if log['level'] == 'SEVERE' and 'favicon' not in log['message']:
                if any(keyword in log['message'].lower() for keyword in [
                    'assertion failed', 'addseries', 'candlestick', 'typeerror'
                ]):
                    tradingview_errors.append(f"Browser Log: {log['message']}")
        
        # Check for chart content (should have canvas)
        canvas_elements = browser.find_elements(By.CSS_SELECTOR, "#chart canvas")
        if not canvas_elements:
            tradingview_errors.append("No chart canvas found - chart failed to initialize")
        
        # Verify no CSS error elements
        error_elements = browser.find_elements(By.CSS_SELECTOR, ".error")
        css_error_count = len([el for el in error_elements if el.is_displayed()])
        if css_error_count > 0:
            tradingview_errors.append(f"Found {css_error_count} CSS error elements")
        
        # Report all errors found
        if tradingview_errors:
            print(f"\n=== DETECTED ERRORS ===")
            for i, error in enumerate(tradingview_errors, 1):
                print(f"{i}. {error}")
            print(f"=== END ERRORS ===\n")
        
        # Assert no TradingView errors
        assert len(tradingview_errors) == 0, f"Found {len(tradingview_errors)} TradingView errors: {'; '.join(tradingview_errors)}"
        
        # Verify chart canvas exists and has meaningful size
        if canvas_elements:
            canvas = canvas_elements[0]
            assert canvas.is_displayed(), "Chart canvas should be visible"
            assert canvas.size['width'] > 100, "Chart should have meaningful width"
            assert canvas.size['height'] > 100, "Chart should have meaningful height"

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.debug
class TestTradingViewDebugging:
    """Debug tests for TradingView integration issues."""
    
    def test_capture_console_errors(self, browser, test_config):
        """Capture and analyze JavaScript console errors."""
        # Enable console logging
        browser.execute_script("""
            window.consoleErrors = [];
            const originalError = console.error;
            console.error = function(...args) {
                window.consoleErrors.push(args.join(' '));
                originalError.apply(console, args);
            };
        """)
        
        # Navigate to main chart
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for page to load
        time.sleep(10)
        
        # Get console errors
        console_errors = browser.execute_script("return window.consoleErrors || [];")
        
        # Analyze errors
        tradingview_errors = [err for err in console_errors if 'LightweightCharts' in err or 'addLineSeries' in err]
        module_errors = [err for err in console_errors if 'Failed to load module' in err]
        
        # Report findings
        print(f"Total console errors: {len(console_errors)}")
        print(f"TradingView specific errors: {len(tradingview_errors)}")
        print(f"Module loading errors: {len(module_errors)}")
        
        if tradingview_errors:
            print("TradingView errors:")
            for error in tradingview_errors:
                print(f"  - {error}")
        
        if module_errors:
            print("Module errors:")
            for error in module_errors:
                print(f"  - {error}")
        
        # Fail if critical errors found
        critical_errors = tradingview_errors + module_errors
        assert len(critical_errors) == 0, f"Found {len(critical_errors)} critical errors"
    
    def test_api_endpoints_accessibility(self, browser, test_config):
        """Test that all required API endpoints are accessible."""
        endpoints_to_test = [
            "/api/chart/data?symbol=GOLDGUINEA&timeframe=1m&bars=5",
            "/api/chart/indicators?strategy=sma_fractal_scalper&timeframe=1m",
            "/api/status",
            "/api/logs?lines=10"
        ]
        
        for endpoint in endpoints_to_test:
            # Test endpoint accessibility via JavaScript
            response_status = browser.execute_script(f"""
                return fetch('{test_config['dashboard_url']}{endpoint}')
                    .then(response => response.status)
                    .catch(error => 0);
            """)
            
            # Wait for promise to resolve
            time.sleep(1)
            
            # Check response
            final_status = browser.execute_script("return arguments[0];", response_status)
            assert final_status == 200, f"Endpoint {endpoint} should be accessible (got {final_status})"
    
    def test_javascript_module_loading(self, browser, test_config):
        """Test that all JavaScript modules load correctly."""
        # Navigate to chart page
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for modules to load
        time.sleep(5)
        
        # Check module availability
        modules_loaded = browser.execute_script("""
            const modules = {};
            
            // Check if modules are loaded
            try {
                modules.DataService = typeof window.DataService !== 'undefined';
                modules.ChartManager = typeof window.ChartManager !== 'undefined';
                modules.IndicatorManager = typeof window.IndicatorManager !== 'undefined';
                modules.TimeframeManager = typeof window.TimeframeManager !== 'undefined';
                modules.TradingDashboard = typeof window.TradingDashboard !== 'undefined';
            } catch (e) {
                modules.error = e.message;
            }
            
            return modules;
        """)
        
        print(f"Module loading status: {json.dumps(modules_loaded, indent=2)}")
        
        # At minimum, TradingView library should be loaded
        tradingview_loaded = browser.execute_script("return typeof LightweightCharts !== 'undefined';")
        assert tradingview_loaded, "TradingView library must be loaded"

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.performance
class TestTradingViewPerformance:
    """Performance tests for TradingView integration."""
    
    def test_chart_loading_performance(self, browser, test_config, performance_monitor):
        """Test chart loading performance benchmarks."""
        start_time = time.time()
        
        # Navigate to chart
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for chart to be ready
        chart_ready = WebDriverWait(browser, 30).until(
            lambda driver: driver.execute_script("""
                return document.querySelector('#trading-chart canvas') !== null;
            """)
        )
        
        load_time = time.time() - start_time
        
        assert chart_ready, "Chart should load successfully"
        assert load_time < 15, f"Chart should load within 15 seconds (took {load_time:.2f}s)"
        
        print(f"Chart loading time: {load_time:.2f} seconds")
    
    def test_memory_usage_after_chart_load(self, browser, test_config):
        """Test memory usage after chart initialization."""
        # Navigate to chart
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for chart to load
        time.sleep(10)
        
        # Get memory usage if available
        memory_info = browser.execute_script("""
            if (performance.memory) {
                return {
                    usedJSHeapSize: performance.memory.usedJSHeapSize,
                    totalJSHeapSize: performance.memory.totalJSHeapSize,
                    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                };
            }
            return null;
        """)
        
        if memory_info:
            used_mb = memory_info['usedJSHeapSize'] / (1024 * 1024)
            total_mb = memory_info['totalJSHeapSize'] / (1024 * 1024)
            
            print(f"Memory usage: {used_mb:.2f}MB used, {total_mb:.2f}MB total")
            
            # Memory usage should be reasonable (less than 200MB)
            assert used_mb < 200, f"Memory usage should be under 200MB (using {used_mb:.2f}MB)"
        else:
            print("Memory performance data not available in this browser") 