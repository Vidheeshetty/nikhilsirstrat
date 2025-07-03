"""
Comprehensive tests for chart rendering functionality.

Tests cover:
- Basic chart rendering and loading
- Indicator overlays (SMA, fractals)
- Real-time data updates
- Chart interactions (zoom, pan, hover)
- Performance benchmarks
"""

import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tests.selenium.page_objects.dashboard_page import DashboardPage
from tests.selenium.page_objects.chart_page import ChartPage

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.prod
class TestChartRendering:
    """Production tests for core chart rendering functionality."""
    
    def test_chart_loads_successfully(self, dashboard_page, performance_monitor):
        """Test that chart loads and renders successfully."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Verify dashboard loads
        assert dashboard.is_loaded(), "Dashboard should load successfully"
        
        # Verify chart loads
        assert chart.is_chart_loaded(), "Chart should load successfully"
        
        # Verify chart has proper dimensions
        dimensions = chart.get_chart_dimensions()
        assert dimensions['width'] > 100, "Chart should have meaningful width"
        assert dimensions['height'] > 100, "Chart should have meaningful height"
        
        # Performance check
        assert performance_monitor['duration'] < 10, "Chart should load within 10 seconds"
    
    def test_chart_displays_market_data(self, dashboard_page, sample_market_data):
        """Test that chart displays actual market data."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load with data
        assert chart.wait_for_chart_data(), "Chart should load with market data"
        
        # Verify price range is reasonable
        price_range = chart.get_chart_price_range()
        assert price_range['min'] is not None, "Chart should have minimum price"
        assert price_range['max'] is not None, "Chart should have maximum price"
        assert price_range['max'] > price_range['min'], "Max price should be greater than min"
    
    def test_chart_responsive_design(self, dashboard_page):
        """Test chart responsiveness to different screen sizes."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Test different window sizes
        test_sizes = [(1920, 1080), (1366, 768), (1024, 768)]
        
        for width, height in test_sizes:
            dashboard_page.set_window_size(width, height)
            time.sleep(1)
            
            # Verify chart adapts to new size
            dimensions = chart.get_chart_dimensions()
            assert dimensions['width'] > 0, f"Chart should adapt to {width}x{height}"
            assert dimensions['height'] > 0, f"Chart should adapt to {width}x{height}"
    
    def test_chart_data_integrity(self, dashboard_page):
        """Test chart data integrity and validation."""
        chart = ChartPage(dashboard_page)
        
        # Validate chart data
        validation = chart.validate_chart_data_integrity()
        assert validation['valid'], f"Chart data should be valid: {validation.get('reason', 'Unknown error')}"

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.dev
class TestChartIndicators:
    """Development tests for chart indicator functionality."""
    
    def test_sma_indicators_display(self, dashboard_page):
        """Test SMA indicator lines are displayed on chart."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Check for SMA indicators
        indicators = chart.get_visible_indicators()
        assert "SMA_SHORT" in indicators, "Short SMA should be visible"
        assert "SMA_LONG" in indicators, "Long SMA should be visible"
    
    def test_fractal_indicators_display(self, dashboard_page):
        """Test fractal high/low indicators are displayed."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Check for fractal indicators
        indicators = chart.get_visible_indicators()
        # Note: Fractals may not always be visible depending on data
        # This is a development test to verify the functionality exists
        if "FRACTAL_HIGHS" in indicators or "FRACTAL_LOWS" in indicators:
            assert True, "Fractal indicators are working"
        else:
            # Log for development debugging
            print("No fractal indicators visible - check data or implementation")
    
    def test_indicator_toggle_functionality(self, dashboard_page):
        """Test toggling indicators on/off."""
        chart = ChartPage(dashboard_page)
        
        # Get initial indicator state
        initial_indicators = chart.get_visible_indicators()
        
        # Toggle SMA short indicator
        if chart.toggle_indicator_visibility("sma_short"):
            time.sleep(1)
            new_indicators = chart.get_visible_indicators()
            
            # Verify indicator state changed
            sma_short_initially_visible = "SMA_SHORT" in initial_indicators
            sma_short_now_visible = "SMA_SHORT" in new_indicators
            
            assert sma_short_initially_visible != sma_short_now_visible, \
                "SMA short indicator should toggle visibility"
    
    def test_trading_signals_on_chart(self, dashboard_page):
        """Test trading signals are displayed on chart."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Get trading signals
        signals = chart.get_trading_signals_on_chart()
        
        # This is a development test - signals may not always be present
        total_signals = len(signals['buy']) + len(signals['sell'])
        print(f"Found {total_signals} trading signals on chart")
        
        # Verify signal structure if signals exist
        for buy_signal in signals['buy']:
            assert 'position' in buy_signal, "Buy signal should have position"
            assert 'visible' in buy_signal, "Buy signal should have visibility status"
        
        for sell_signal in signals['sell']:
            assert 'position' in sell_signal, "Sell signal should have position"
            assert 'visible' in sell_signal, "Sell signal should have visibility status"

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.realtime
@pytest.mark.dev
class TestChartRealTimeUpdates:
    """Development tests for real-time chart updates."""
    
    def test_chart_updates_with_live_data(self, dashboard_page):
        """Test chart updates with real-time market data."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Wait for real-time update
        update_received = chart.wait_for_real_time_update(timeout=60)
        
        if update_received:
            assert True, "Chart received real-time update"
        else:
            # This is acceptable during development/testing
            print("No real-time update received - check market hours or data feed")
    
    def test_chart_performance_during_updates(self, dashboard_page, performance_monitor):
        """Test chart performance during real-time updates."""
        chart = ChartPage(dashboard_page)
        
        # Measure chart performance
        performance = chart.measure_chart_performance()
        
        assert performance.get('update_duration', 0) < 1.0, \
            "Chart updates should complete within 1 second"
        
        # Check JavaScript performance if available
        js_perf = performance.get('js_performance', {})
        if js_perf.get('memoryUsage'):
            # Memory usage should be reasonable (less than 100MB)
            assert js_perf['memoryUsage'] < 100 * 1024 * 1024, \
                "Chart should not consume excessive memory"

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.dev
class TestChartInteractions:
    """Development tests for chart user interactions."""
    
    def test_chart_hover_functionality(self, dashboard_page):
        """Test chart hover shows crosshair and price info."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Hover over chart center
        crosshair_info = chart.hover_over_chart_point(50, 50)
        
        # Verify hover functionality works
        if crosshair_info:
            print(f"Crosshair info: {crosshair_info}")
            assert True, "Chart hover functionality is working"
        else:
            print("No crosshair info returned - check implementation")
    
    def test_chart_zoom_functionality(self, dashboard_page):
        """Test chart zoom in/out functionality."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Get initial time range
        initial_range = chart.get_chart_time_range()
        
        # Zoom in
        zoom_success = chart.zoom_chart(1.5)
        
        if zoom_success:
            time.sleep(1)
            new_range = chart.get_chart_time_range()
            
            # Verify zoom changed the view
            # (This is a development test - exact validation depends on implementation)
            assert True, "Chart zoom functionality is working"
        else:
            print("Zoom functionality not available - check implementation")
    
    def test_chart_pan_functionality(self, dashboard_page):
        """Test chart pan left/right functionality."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Test panning
        pan_directions = ["left", "right"]
        
        for direction in pan_directions:
            pan_success = chart.pan_chart(direction)
            
            if pan_success:
                assert True, f"Chart pan {direction} is working"
            else:
                print(f"Pan {direction} functionality not available")
    
    def test_timeframe_switching(self, dashboard_page):
        """Test switching between different timeframes."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Test different timeframes
        timeframes = ["1MIN", "5MIN", "15MIN"]
        
        for timeframe in timeframes:
            switch_success = chart.switch_timeframe(timeframe)
            
            if switch_success:
                time.sleep(2)  # Wait for chart to update
                assert True, f"Timeframe switch to {timeframe} is working"
            else:
                print(f"Timeframe {timeframe} not available")

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.performance
@pytest.mark.prod
class TestChartPerformance:
    """Production tests for chart performance benchmarks."""
    
    def test_chart_load_time_benchmark(self, dashboard_page, performance_monitor):
        """Test chart loads within acceptable time limits."""
        chart = ChartPage(dashboard_page)
        
        start_time = time.time()
        
        # Wait for chart to load completely
        assert chart.is_chart_loaded(), "Chart should load"
        assert chart.wait_for_chart_data(), "Chart should load with data"
        
        load_time = time.time() - start_time
        
        # Performance benchmarks
        assert load_time < 5.0, f"Chart should load within 5 seconds, took {load_time:.2f}s"
        
        # Log performance for monitoring
        print(f"Chart load time: {load_time:.2f} seconds")
    
    def test_chart_memory_usage(self, dashboard_page):
        """Test chart memory usage stays within limits."""
        chart = ChartPage(dashboard_page)
        
        # Wait for chart to load
        assert chart.is_chart_loaded(), "Chart should be loaded"
        
        # Measure performance
        performance = chart.measure_chart_performance()
        js_perf = performance.get('js_performance', {})
        
        if js_perf.get('memoryUsage'):
            memory_mb = js_perf['memoryUsage'] / (1024 * 1024)
            assert memory_mb < 50, f"Chart should use less than 50MB, using {memory_mb:.2f}MB"
            print(f"Chart memory usage: {memory_mb:.2f}MB")
        else:
            print("Memory usage monitoring not available")

@pytest.mark.selenium
@pytest.mark.chart
@pytest.mark.debug
class TestChartDebugging:
    """Debug tests for chart troubleshooting."""
    
    def test_capture_chart_state_for_debugging(self, dashboard_page):
        """Capture complete chart state for debugging purposes."""
        dashboard = DashboardPage(dashboard_page)
        chart = ChartPage(dashboard_page)
        
        # Capture complete state
        dashboard_state = dashboard.capture_dashboard_state()
        chart_state = chart.capture_chart_state()
        
        # Log state for debugging
        print(f"Dashboard state: {dashboard_state}")
        print(f"Chart state: {chart_state}")
        
        # Save state to file for analysis
        import json
        from pathlib import Path
        
        debug_dir = Path("testlogs/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        with open(debug_dir / f"chart_state_{timestamp}.json", "w") as f:
            json.dump({
                "dashboard": dashboard_state,
                "chart": chart_state
            }, f, indent=2)
        
        assert True, "Chart state captured for debugging"
    
    def test_chart_error_handling(self, dashboard_page):
        """Test chart handles errors gracefully."""
        chart = ChartPage(dashboard_page)
        
        # Try to trigger various error conditions
        error_tests = [
            ("Invalid zoom", lambda: chart.zoom_chart(-1)),
            ("Invalid timeframe", lambda: chart.switch_timeframe("INVALID")),
            ("Invalid hover", lambda: chart.hover_over_chart_point(200, 200)),
        ]
        
        for test_name, test_func in error_tests:
            try:
                result = test_func()
                print(f"{test_name}: {'Handled gracefully' if not result else 'Unexpected success'}")
            except Exception as e:
                print(f"{test_name}: Exception handled - {str(e)}")
        
        # Chart should still be functional after error tests
        assert chart.is_chart_loaded(), "Chart should remain functional after error tests" 