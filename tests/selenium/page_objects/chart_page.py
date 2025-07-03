"""
Page Object Model for Chart Component.

Specialized page object for testing TradingView Lightweight Charts functionality,
including chart rendering, indicator overlays, real-time updates, and user interactions.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from typing import Dict, List, Optional, Any, Tuple
import time
import json

class ChartPage:
    """Page object for chart-specific interactions."""
    
    # Chart container locators
    CHART_CONTAINER = (By.ID, "chart-container")
    CHART_CANVAS = (By.CSS_SELECTOR, "#chart-container canvas")
    CHART_WRAPPER = (By.CSS_SELECTOR, ".tv-lightweight-charts")
    
    # Indicator overlays
    SMA_SHORT_LINE = (By.CSS_SELECTOR, ".sma-short-line")
    SMA_LONG_LINE = (By.CSS_SELECTOR, ".sma-long-line")
    FRACTAL_HIGHS = (By.CSS_SELECTOR, ".fractal-high")
    FRACTAL_LOWS = (By.CSS_SELECTOR, ".fractal-low")
    
    # Trading signals on chart
    BUY_MARKERS = (By.CSS_SELECTOR, ".buy-marker")
    SELL_MARKERS = (By.CSS_SELECTOR, ".sell-marker")
    STOP_LOSS_LINES = (By.CSS_SELECTOR, ".stop-loss-line")
    
    # Chart controls
    TIMEFRAME_BUTTONS = (By.CSS_SELECTOR, ".timeframe-button")
    INDICATOR_PANEL = (By.ID, "indicator-panel")
    CHART_SETTINGS = (By.ID, "chart-settings")
    
    # Price display elements
    PRICE_SCALE = (By.CSS_SELECTOR, ".price-scale")
    TIME_SCALE = (By.CSS_SELECTOR, ".time-scale")
    CROSSHAIR = (By.CSS_SELECTOR, ".crosshair")
    PRICE_LINE = (By.CSS_SELECTOR, ".price-line")
    
    def __init__(self, driver: WebDriver, timeout: int = 30):
        """Initialize chart page object."""
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
        self.actions = ActionChains(driver)
    
    def is_chart_loaded(self) -> bool:
        """Check if chart is fully loaded and rendered."""
        try:
            # Wait for chart container
            self.wait.until(EC.presence_of_element_located(self.CHART_CONTAINER))
            
            # Wait for canvas element
            self.wait.until(EC.presence_of_element_located(self.CHART_CANVAS))
            
            # Check if chart has actual dimensions
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            return canvas.size['width'] > 100 and canvas.size['height'] > 100
        except TimeoutException:
            return False
    
    def wait_for_chart_data(self, timeout: int = 15) -> bool:
        """Wait for chart to load with actual market data."""
        try:
            # Execute JavaScript to check if chart has data
            start_time = time.time()
            while time.time() - start_time < timeout:
                has_data = self.driver.execute_script("""
                    try {
                        // Check if chart instance exists and has data
                        if (window.chartManager && window.chartManager.chart) {
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                """)
                
                if has_data:
                    return True
                time.sleep(1)
            
            return False
        except Exception:
            return False
    
    def get_chart_dimensions(self) -> Dict[str, int]:
        """Get chart canvas dimensions."""
        try:
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            return {
                "width": canvas.size['width'],
                "height": canvas.size['height'],
                "x": canvas.location['x'],
                "y": canvas.location['y']
            }
        except Exception:
            return {"width": 0, "height": 0, "x": 0, "y": 0}
    
    def get_visible_indicators(self) -> List[str]:
        """Get list of currently visible indicators."""
        indicators = []
        
        try:
            # Check SMA indicators
            if self._is_element_visible(self.SMA_SHORT_LINE):
                indicators.append("SMA_SHORT")
            if self._is_element_visible(self.SMA_LONG_LINE):
                indicators.append("SMA_LONG")
            
            # Check fractal indicators
            if self._is_element_visible(self.FRACTAL_HIGHS):
                indicators.append("FRACTAL_HIGHS")
            if self._is_element_visible(self.FRACTAL_LOWS):
                indicators.append("FRACTAL_LOWS")
        except Exception:
            pass
        
        return indicators
    
    def get_trading_signals_on_chart(self) -> Dict[str, List[Dict]]:
        """Get trading signals displayed on chart."""
        signals = {"buy": [], "sell": []}
        
        try:
            # Get buy markers
            buy_markers = self.driver.find_elements(*self.BUY_MARKERS)
            for marker in buy_markers:
                if marker.is_displayed():
                    signals["buy"].append({
                        "position": marker.location,
                        "visible": True,
                        "tooltip": marker.get_attribute("title") or ""
                    })
            
            # Get sell markers
            sell_markers = self.driver.find_elements(*self.SELL_MARKERS)
            for marker in sell_markers:
                if marker.is_displayed():
                    signals["sell"].append({
                        "position": marker.location,
                        "visible": True,
                        "tooltip": marker.get_attribute("title") or ""
                    })
        except Exception:
            pass
        
        return signals
    
    def hover_over_chart_point(self, x_percent: float, y_percent: float) -> Dict[str, Any]:
        """Hover over a specific point on the chart and get crosshair info."""
        try:
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            
            # Calculate absolute position
            width = canvas.size['width']
            height = canvas.size['height']
            x_offset = int(width * x_percent / 100)
            y_offset = int(height * y_percent / 100)
            
            # Move to position
            self.actions.move_to_element_with_offset(canvas, x_offset, y_offset).perform()
            time.sleep(0.5)
            
            # Get crosshair information via JavaScript
            crosshair_info = self.driver.execute_script("""
                try {
                    if (window.chartManager && window.chartManager.getCrosshairInfo) {
                        return window.chartManager.getCrosshairInfo();
                    }
                    return null;
                } catch (e) {
                    return null;
                }
            """)
            
            return crosshair_info or {}
        except Exception:
            return {}
    
    def click_chart_point(self, x_percent: float, y_percent: float) -> bool:
        """Click on a specific point on the chart."""
        try:
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            
            # Calculate absolute position
            width = canvas.size['width']
            height = canvas.size['height']
            x_offset = int(width * x_percent / 100)
            y_offset = int(height * y_percent / 100)
            
            # Click position
            self.actions.move_to_element_with_offset(canvas, x_offset, y_offset).click().perform()
            time.sleep(0.5)
            return True
        except Exception:
            return False
    
    def zoom_chart(self, zoom_factor: float) -> bool:
        """Zoom chart by specified factor."""
        try:
            result = self.driver.execute_script(f"""
                try {{
                    if (window.chartManager && window.chartManager.zoom) {{
                        window.chartManager.zoom({zoom_factor});
                        return true;
                    }}
                    return false;
                }} catch (e) {{
                    return false;
                }}
            """)
            time.sleep(1)
            return result
        except Exception:
            return False
    
    def pan_chart(self, direction: str, amount: int = 50) -> bool:
        """Pan chart in specified direction."""
        try:
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            
            # Calculate drag coordinates based on direction
            start_x = canvas.size['width'] // 2
            start_y = canvas.size['height'] // 2
            
            if direction == "left":
                end_x = start_x - amount
                end_y = start_y
            elif direction == "right":
                end_x = start_x + amount
                end_y = start_y
            elif direction == "up":
                end_x = start_x
                end_y = start_y - amount
            elif direction == "down":
                end_x = start_x
                end_y = start_y + amount
            else:
                return False
            
            # Perform drag
            self.actions.move_to_element_with_offset(canvas, start_x, start_y)\
                       .click_and_hold()\
                       .move_by_offset(end_x - start_x, end_y - start_y)\
                       .release()\
                       .perform()
            
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def get_chart_price_range(self) -> Dict[str, Optional[float]]:
        """Get visible price range on chart."""
        try:
            price_range = self.driver.execute_script("""
                try {
                    if (window.chartManager && window.chartManager.getPriceRange) {
                        return window.chartManager.getPriceRange();
                    }
                    return null;
                } catch (e) {
                    return null;
                }
            """)
            
            return price_range or {"min": None, "max": None}
        except Exception:
            return {"min": None, "max": None}
    
    def get_chart_time_range(self) -> Dict[str, Optional[str]]:
        """Get visible time range on chart."""
        try:
            time_range = self.driver.execute_script("""
                try {
                    if (window.chartManager && window.chartManager.getTimeRange) {
                        return window.chartManager.getTimeRange();
                    }
                    return null;
                } catch (e) {
                    return null;
                }
            """)
            
            return time_range or {"start": None, "end": None}
        except Exception:
            return {"start": None, "end": None}
    
    def switch_timeframe(self, timeframe: str) -> bool:
        """Switch chart timeframe."""
        try:
            # Find timeframe button
            timeframe_button = self.driver.find_element(
                By.CSS_SELECTOR, f".timeframe-button[data-timeframe='{timeframe}']"
            )
            timeframe_button.click()
            
            # Wait for chart to update
            time.sleep(2)
            return True
        except Exception:
            return False
    
    def toggle_indicator_visibility(self, indicator: str) -> bool:
        """Toggle indicator visibility on chart."""
        try:
            toggle_button = self.driver.find_element(
                By.CSS_SELECTOR, f".indicator-toggle[data-indicator='{indicator}']"
            )
            toggle_button.click()
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def measure_chart_performance(self) -> Dict[str, Any]:
        """Measure chart rendering performance."""
        try:
            # Start performance measurement
            start_time = time.time()
            
            # Trigger chart update
            self.driver.execute_script("""
                if (window.chartManager && window.chartManager.forceUpdate) {
                    window.chartManager.forceUpdate();
                }
            """)
            
            # Wait for update to complete
            time.sleep(1)
            
            end_time = time.time()
            
            # Get performance metrics via JavaScript
            performance_data = self.driver.execute_script("""
                try {
                    return {
                        renderTime: performance.now(),
                        memoryUsage: performance.memory ? performance.memory.usedJSHeapSize : null,
                        chartReady: window.chartManager ? true : false
                    };
                } catch (e) {
                    return {};
                }
            """)
            
            return {
                "update_duration": end_time - start_time,
                "js_performance": performance_data,
                "timestamp": time.time()
            }
        except Exception:
            return {}
    
    def wait_for_real_time_update(self, timeout: int = 30) -> bool:
        """Wait for real-time chart update."""
        try:
            # Get initial chart state
            initial_state = self.driver.execute_script("""
                try {
                    if (window.chartManager && window.chartManager.getLastUpdateTime) {
                        return window.chartManager.getLastUpdateTime();
                    }
                    return Date.now();
                } catch (e) {
                    return Date.now();
                }
            """)
            
            # Wait for state to change
            start_time = time.time()
            while time.time() - start_time < timeout:
                current_state = self.driver.execute_script("""
                    try {
                        if (window.chartManager && window.chartManager.getLastUpdateTime) {
                            return window.chartManager.getLastUpdateTime();
                        }
                        return Date.now();
                    } catch (e) {
                        return Date.now();
                    }
                """)
                
                if current_state != initial_state:
                    return True
                time.sleep(1)
            
            return False
        except Exception:
            return False
    
    def validate_chart_data_integrity(self) -> Dict[str, Any]:
        """Validate chart data integrity."""
        try:
            validation_result = self.driver.execute_script("""
                try {
                    if (window.chartManager && window.chartManager.validateData) {
                        return window.chartManager.validateData();
                    }
                    return {valid: false, reason: "No validation method available"};
                } catch (e) {
                    return {valid: false, reason: e.message};
                }
            """)
            
            return validation_result or {"valid": False, "reason": "Unknown error"}
        except Exception:
            return {"valid": False, "reason": "Exception during validation"}
    
    def _is_element_visible(self, locator: Tuple[By, str]) -> bool:
        """Check if element is visible on page."""
        try:
            element = self.driver.find_element(*locator)
            return element.is_displayed()
        except Exception:
            return False
    
    def capture_chart_state(self) -> Dict[str, Any]:
        """Capture complete chart state for debugging."""
        return {
            "chart_loaded": self.is_chart_loaded(),
            "chart_dimensions": self.get_chart_dimensions(),
            "visible_indicators": self.get_visible_indicators(),
            "trading_signals": self.get_trading_signals_on_chart(),
            "price_range": self.get_chart_price_range(),
            "time_range": self.get_chart_time_range(),
            "performance": self.measure_chart_performance(),
            "data_integrity": self.validate_chart_data_integrity(),
            "timestamp": time.time()
        } 