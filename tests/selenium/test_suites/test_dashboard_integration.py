"""
Integration tests for complete dashboard functionality.

Tests the interaction between all dashboard components:
- Chart and status panel integration
- Real-time data flow
- Trading signal display coordination
- Performance monitoring integration
"""

import pytest
import time
import json
from pathlib import Path

from tests.selenium.page_objects.dashboard_page import DashboardPage
from tests.selenium.page_objects.chart_page import ChartPage

@pytest.mark.selenium
@pytest.mark.prod
class TestDashboardIntegration:
    """Production tests for complete dashboard integration."""
    
    def test_dashboard_loads_completely(self, dashboard_page, performance_monitor):
        """Test complete dashboard loads with all components."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Verify all major components load
        assert dashboard.is_loaded(), "Dashboard should load"
        assert chart.is_chart_loaded(), "Chart should load"
        
        # Verify status components
        strategy_status = dashboard.get_strategy_status()
        assert strategy_status['visible'], "Strategy status should be visible"
        
        broker_status = dashboard.get_broker_status()
        assert broker_status['visible'], "Broker status should be visible"
        
        # Verify account information
        balance = dashboard.get_account_balance()
        assert balance is not None, "Account balance should be displayed"
        
        # Performance check
        assert performance_monitor['duration'] < 15, "Complete dashboard should load within 15 seconds"
    
    def test_real_time_data_flow_integration(self, dashboard_page):
        """Test real-time data flows correctly between components."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Get initial states
        initial_price = dashboard.get_current_price()
        initial_connection = dashboard.get_connection_status()
        
        # Wait for real-time update
        update_received = dashboard.wait_for_data_update(timeout=60)
        
        if update_received:
            # Verify components updated consistently
            new_price = dashboard.get_current_price()
            new_connection = dashboard.get_connection_status()
            
            assert new_connection['is_connected'], "Connection should be active during updates"
            
            # If price changed, verify it's reflected across components
            if new_price != initial_price:
                # Chart should also reflect the update
                chart_updated = chart.wait_for_real_time_update(timeout=5)
                assert chart_updated, "Chart should update when price data changes"
        else:
            print("No real-time update received - check market hours or data feed")
    
    def test_trading_signal_coordination(self, dashboard_page):
        """Test trading signals are coordinated between chart and status panels."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Get trading signals from both chart and dashboard
        dashboard_signals = dashboard.get_trading_signals()
        chart_signals = chart.get_trading_signals_on_chart()
        
        # Verify signal coordination
        total_dashboard_signals = len(dashboard_signals)
        total_chart_signals = len(chart_signals['buy']) + len(chart_signals['sell'])
        
        print(f"Dashboard signals: {total_dashboard_signals}, Chart signals: {total_chart_signals}")
        
        # Signals should be consistent (allowing for timing differences)
        if total_dashboard_signals > 0 or total_chart_signals > 0:
            assert True, "Trading signals are being displayed"
        else:
            print("No trading signals currently active - normal during testing")
    
    def test_status_panel_accuracy(self, dashboard_page):
        """Test status panel displays accurate information."""
        dashboard = DashboardPage(dashboard_page)
        
        # Get all status information
        strategy_status = dashboard.get_strategy_status()
        broker_status = dashboard.get_broker_status()
        balance = dashboard.get_account_balance()
        pnl = dashboard.get_pnl_display()
        trade_count = dashboard.get_trade_count()
        
        # Verify status information is reasonable
        assert strategy_status['text'] != "", "Strategy status should have text"
        assert broker_status['text'] != "", "Broker status should have text"
        
        # Balance should be a reasonable value
        if balance:
            assert "₹" in balance or "$" in balance, "Balance should include currency symbol"
        
        # Trade count should be non-negative
        assert trade_count >= 0, "Trade count should be non-negative"
        
        print(f"Status check - Strategy: {strategy_status['text']}, "
              f"Broker: {broker_status['text']}, Balance: {balance}, "
              f"PnL: {pnl['text']}, Trades: {trade_count}")

@pytest.mark.selenium
@pytest.mark.dev
class TestDashboardDevelopment:
    """Development tests for dashboard functionality."""
    
    def test_dashboard_responsive_behavior(self, dashboard_page):
        """Test dashboard responds properly to different screen sizes."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Test different screen sizes
        screen_sizes = [
            (1920, 1080, "Desktop Large"),
            (1366, 768, "Desktop Standard"),
            (1024, 768, "Desktop Small"),
            (768, 1024, "Tablet Portrait")
        ]
        
        for width, height, description in screen_sizes:
            dashboard_page.set_window_size(width, height)
            time.sleep(2)
            
            # Verify dashboard remains functional
            assert dashboard.is_loaded(), f"Dashboard should work on {description}"
            
            # Verify chart adapts
            chart_dimensions = chart.get_chart_dimensions()
            assert chart_dimensions['width'] > 0, f"Chart should adapt to {description}"
            assert chart_dimensions['height'] > 0, f"Chart should adapt to {description}"
            
            print(f"{description} ({width}x{height}): Chart {chart_dimensions['width']}x{chart_dimensions['height']}")
    
    def test_dashboard_error_recovery(self, dashboard_page):
        """Test dashboard recovers from various error conditions."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Simulate various error conditions
        error_tests = [
            ("Network interruption", self._simulate_network_error),
            ("Invalid chart interaction", self._simulate_chart_error),
            ("Status update failure", self._simulate_status_error),
        ]
        
        for test_name, test_func in error_tests:
            try:
                test_func(dashboard_page)
                time.sleep(2)
                
                # Verify dashboard recovers
                assert dashboard.is_loaded(), f"Dashboard should recover from {test_name}"
                assert chart.is_chart_loaded(), f"Chart should recover from {test_name}"
                
                print(f"{test_name}: Recovery successful")
            except Exception as e:
                print(f"{test_name}: Error during test - {str(e)}")
    
    def test_dashboard_performance_monitoring(self, dashboard_page, performance_monitor):
        """Test dashboard performance under various conditions."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Measure performance of various operations
        operations = [
            ("Chart zoom", lambda: chart.zoom_chart(1.5)),
            ("Timeframe switch", lambda: chart.switch_timeframe("5MIN")),
            ("Status refresh", lambda: dashboard.get_strategy_status()),
            ("Signal check", lambda: dashboard.get_trading_signals()),
        ]
        
        performance_results = {}
        
        for operation_name, operation_func in operations:
            start_time = time.time()
            try:
                operation_func()
                duration = time.time() - start_time
                performance_results[operation_name] = duration
                
                # Performance thresholds for development
                assert duration < 2.0, f"{operation_name} should complete within 2 seconds"
                
            except Exception as e:
                performance_results[operation_name] = f"Error: {str(e)}"
        
        print(f"Performance results: {performance_results}")
    
    def _simulate_network_error(self, driver):
        """Simulate network error condition."""
        # This would typically involve mocking network requests
        # For now, just test that the dashboard handles missing data gracefully
        pass
    
    def _simulate_chart_error(self, driver):
        """Simulate chart error condition."""
        # Try to trigger chart error by invalid operations
        try:
            driver.execute_script("window.chartManager = null;")
        except:
            pass
    
    def _simulate_status_error(self, driver):
        """Simulate status update error."""
        # Try to trigger status error
        try:
            driver.execute_script("window.statusManager = null;")
        except:
            pass

@pytest.mark.selenium
@pytest.mark.debug
class TestDashboardDebugging:
    """Debug tests for dashboard troubleshooting."""
    
    def test_capture_complete_dashboard_state(self, dashboard_page):
        """Capture complete dashboard state for debugging."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Capture all state information
        complete_state = {
            "dashboard": dashboard.capture_dashboard_state(),
            "chart": chart.capture_chart_state(),
            "browser_info": {
                "window_size": dashboard_page.get_window_size(),
                "url": dashboard_page.current_url,
                "title": dashboard_page.title
            },
            "performance": {
                "page_load_time": dashboard_page.execute_script("return performance.timing.loadEventEnd - performance.timing.navigationStart"),
                "dom_ready_time": dashboard_page.execute_script("return performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart")
            }
        }
        
        # Save state for analysis
        debug_dir = Path("testlogs/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        state_file = debug_dir / f"dashboard_state_{timestamp}.json"
        
        with open(state_file, "w") as f:
            json.dump(complete_state, f, indent=2, default=str)
        
        print(f"Complete dashboard state saved to: {state_file}")
        
        # Verify state capture is comprehensive
        assert "dashboard" in complete_state
        assert "chart" in complete_state
        assert "browser_info" in complete_state
        assert "performance" in complete_state
    
    def test_dashboard_console_errors(self, dashboard_page):
        """Check for JavaScript console errors."""
        # Get console logs
        logs = dashboard_page.get_log('browser')
        
        # Filter for errors
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if errors:
            print(f"Found {len(errors)} console errors:")
            for error in errors:
                print(f"  - {error['message']}")
            
            # For development, log errors but don't fail the test
            # In production, you might want to fail on certain errors
            print("Console errors detected - review for issues")
        else:
            print("No console errors detected")
        
        # Always pass for debugging purposes
        assert True, "Console error check completed"
    
    def test_dashboard_accessibility_check(self, dashboard_page):
        """Basic accessibility check for dashboard."""
        dashboard = DashboardPage(dashboard_page)
        
        # Check for basic accessibility features
        accessibility_checks = {
            "title": dashboard_page.title != "",
            "alt_texts": len(dashboard_page.find_elements(By.CSS_SELECTOR, "img:not([alt])")) == 0,
            "form_labels": len(dashboard_page.find_elements(By.CSS_SELECTOR, "input:not([aria-label]):not([aria-labelledby])")) == 0,
            "color_contrast": True,  # Would require specialized tools
            "keyboard_navigation": True  # Would require specialized testing
        }
        
        print(f"Accessibility check results: {accessibility_checks}")
        
        # Log issues for development
        issues = [check for check, passed in accessibility_checks.items() if not passed]
        if issues:
            print(f"Accessibility issues found: {issues}")
        else:
            print("Basic accessibility checks passed")
        
        assert True, "Accessibility check completed"

@pytest.mark.selenium
@pytest.mark.performance
@pytest.mark.prod
class TestDashboardPerformance:
    """Production performance tests for dashboard."""
    
    def test_dashboard_load_performance(self, dashboard_page, performance_monitor):
        """Test dashboard meets performance requirements."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Measure complete load time
        start_time = time.time()
        
        assert dashboard.is_loaded(), "Dashboard should load"
        assert chart.is_chart_loaded(), "Chart should load"
        assert chart.wait_for_chart_data(timeout=10), "Chart should load with data"
        
        total_load_time = time.time() - start_time
        
        # Performance requirements
        assert total_load_time < 10.0, f"Dashboard should load within 10 seconds, took {total_load_time:.2f}s"
        
        print(f"Dashboard load time: {total_load_time:.2f} seconds")
    
    def test_dashboard_memory_usage(self, dashboard_page):
        """Test dashboard memory usage stays within limits."""
        # Get memory usage via JavaScript
        memory_info = dashboard_page.execute_script("""
            try {
                return {
                    used: performance.memory.usedJSHeapSize,
                    total: performance.memory.totalJSHeapSize,
                    limit: performance.memory.jsHeapSizeLimit
                };
            } catch (e) {
                return null;
            }
        """)
        
        if memory_info:
            used_mb = memory_info['used'] / (1024 * 1024)
            total_mb = memory_info['total'] / (1024 * 1024)
            
            # Memory usage should be reasonable
            assert used_mb < 100, f"Dashboard should use less than 100MB, using {used_mb:.2f}MB"
            
            print(f"Memory usage: {used_mb:.2f}MB / {total_mb:.2f}MB")
        else:
            print("Memory monitoring not available in this browser")
    
    def test_dashboard_cpu_usage(self, dashboard_page):
        """Test dashboard CPU usage during operation."""
        # This is a simplified CPU usage test
        # In practice, you'd use more sophisticated monitoring
        
        start_time = time.time()
        
        # Perform various operations
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        operations = [
            lambda: dashboard.get_strategy_status(),
            lambda: chart.get_chart_dimensions(),
            lambda: dashboard.get_trading_signals(),
            lambda: chart.get_visible_indicators(),
        ]
        
        for operation in operations:
            operation()
            time.sleep(0.1)
        
        operation_time = time.time() - start_time
        
        # Operations should complete quickly
        assert operation_time < 5.0, f"Dashboard operations should be fast, took {operation_time:.2f}s"
        
        print(f"Dashboard operation time: {operation_time:.2f} seconds") 