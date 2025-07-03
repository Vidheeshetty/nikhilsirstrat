"""
Page Object Model for Trading Dashboard.

Encapsulates all dashboard interactions and element locators for clean,
maintainable test code following the Page Object pattern.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from typing import Dict, List, Optional, Any
import time
import json

class DashboardPage:
    """Page object for the trading dashboard."""
    
    # Element locators
    DASHBOARD_CONTAINER = (By.ID, "trading-dashboard")
    CHART_CONTAINER = (By.ID, "chart-container")
    CHART_CANVAS = (By.CSS_SELECTOR, "#chart-container canvas")
    STATUS_PANEL = (By.ID, "status-panel")
    CONTROLS_PANEL = (By.ID, "controls-panel")
    
    # Status elements
    STRATEGY_STATUS = (By.ID, "strategy-status")
    BROKER_STATUS = (By.ID, "broker-status")
    BALANCE_DISPLAY = (By.ID, "account-balance")
    PNL_DISPLAY = (By.ID, "pnl-display")
    TRADE_COUNT = (By.ID, "trade-count")
    
    # Chart controls
    TIMEFRAME_SELECTOR = (By.ID, "timeframe-selector")
    INDICATOR_TOGGLES = (By.CSS_SELECTOR, ".indicator-toggle")
    ZOOM_IN_BUTTON = (By.ID, "zoom-in")
    ZOOM_OUT_BUTTON = (By.ID, "zoom-out")
    RESET_ZOOM_BUTTON = (By.ID, "reset-zoom")
    
    # Real-time data elements
    CURRENT_PRICE = (By.ID, "current-price")
    PRICE_CHANGE = (By.ID, "price-change")
    LAST_UPDATE = (By.ID, "last-update")
    CONNECTION_STATUS = (By.ID, "connection-status")
    
    # Trading signals
    SIGNAL_INDICATORS = (By.CSS_SELECTOR, ".signal-indicator")
    BUY_SIGNALS = (By.CSS_SELECTOR, ".buy-signal")
    SELL_SIGNALS = (By.CSS_SELECTOR, ".sell-signal")
    
    def __init__(self, driver: WebDriver, timeout: int = 30):
        """Initialize dashboard page object."""
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
    
    def is_loaded(self) -> bool:
        """Check if dashboard is fully loaded."""
        try:
            self.wait.until(EC.presence_of_element_located(self.DASHBOARD_CONTAINER))
            self.wait.until(EC.presence_of_element_located(self.CHART_CONTAINER))
            return True
        except TimeoutException:
            return False
    
    def wait_for_chart_render(self) -> bool:
        """Wait for chart to render completely."""
        try:
            # Wait for chart canvas to be present
            self.wait.until(EC.presence_of_element_located(self.CHART_CANVAS))
            
            # Wait for chart to have content (not empty)
            time.sleep(2)  # Allow chart rendering time
            
            # Check if chart has rendered by looking for canvas dimensions
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            return canvas.size['width'] > 0 and canvas.size['height'] > 0
        except TimeoutException:
            return False
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status information."""
        try:
            status_element = self.driver.find_element(*self.STRATEGY_STATUS)
            return {
                "text": status_element.text,
                "is_active": "active" in status_element.get_attribute("class"),
                "visible": status_element.is_displayed()
            }
        except Exception:
            return {"text": "", "is_active": False, "visible": False}
    
    def get_broker_status(self) -> Dict[str, Any]:
        """Get current broker connection status."""
        try:
            status_element = self.driver.find_element(*self.BROKER_STATUS)
            return {
                "text": status_element.text,
                "is_connected": "connected" in status_element.get_attribute("class"),
                "visible": status_element.is_displayed()
            }
        except Exception:
            return {"text": "", "is_connected": False, "visible": False}
    
    def get_account_balance(self) -> Optional[str]:
        """Get current account balance display."""
        try:
            balance_element = self.driver.find_element(*self.BALANCE_DISPLAY)
            return balance_element.text
        except Exception:
            return None
    
    def get_pnl_display(self) -> Dict[str, Any]:
        """Get current P&L display information."""
        try:
            pnl_element = self.driver.find_element(*self.PNL_DISPLAY)
            text = pnl_element.text
            css_class = pnl_element.get_attribute("class")
            
            return {
                "text": text,
                "value": self._extract_numeric_value(text),
                "is_positive": "positive" in css_class,
                "is_negative": "negative" in css_class
            }
        except Exception:
            return {"text": "", "value": 0.0, "is_positive": False, "is_negative": False}
    
    def get_trade_count(self) -> int:
        """Get current trade count."""
        try:
            trade_element = self.driver.find_element(*self.TRADE_COUNT)
            return int(trade_element.text.split()[0])  # Extract number from "5 trades"
        except Exception:
            return 0
    
    def get_current_price(self) -> Optional[float]:
        """Get current price display."""
        try:
            price_element = self.driver.find_element(*self.CURRENT_PRICE)
            return self._extract_numeric_value(price_element.text)
        except Exception:
            return None
    
    def get_price_change(self) -> Dict[str, Any]:
        """Get price change information."""
        try:
            change_element = self.driver.find_element(*self.PRICE_CHANGE)
            text = change_element.text
            css_class = change_element.get_attribute("class")
            
            return {
                "text": text,
                "value": self._extract_numeric_value(text),
                "is_positive": "positive" in css_class or "up" in css_class,
                "is_negative": "negative" in css_class or "down" in css_class
            }
        except Exception:
            return {"text": "", "value": 0.0, "is_positive": False, "is_negative": False}
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get real-time connection status."""
        try:
            status_element = self.driver.find_element(*self.CONNECTION_STATUS)
            css_class = status_element.get_attribute("class")
            
            return {
                "text": status_element.text,
                "is_connected": "connected" in css_class,
                "is_disconnected": "disconnected" in css_class,
                "is_reconnecting": "reconnecting" in css_class
            }
        except Exception:
            return {"text": "", "is_connected": False, "is_disconnected": True, "is_reconnecting": False}
    
    def get_trading_signals(self) -> List[Dict[str, Any]]:
        """Get all visible trading signals."""
        signals = []
        
        try:
            # Get buy signals
            buy_signals = self.driver.find_elements(*self.BUY_SIGNALS)
            for signal in buy_signals:
                signals.append({
                    "type": "BUY",
                    "visible": signal.is_displayed(),
                    "text": signal.text,
                    "position": signal.location
                })
            
            # Get sell signals
            sell_signals = self.driver.find_elements(*self.SELL_SIGNALS)
            for signal in sell_signals:
                signals.append({
                    "type": "SELL",
                    "visible": signal.is_displayed(),
                    "text": signal.text,
                    "position": signal.location
                })
        except Exception:
            pass
        
        return signals
    
    def change_timeframe(self, timeframe: str) -> bool:
        """Change chart timeframe."""
        try:
            selector = self.driver.find_element(*self.TIMEFRAME_SELECTOR)
            selector.click()
            
            # Find and click the timeframe option
            option = self.driver.find_element(By.CSS_SELECTOR, f"option[value='{timeframe}']")
            option.click()
            
            # Wait for chart to update
            time.sleep(2)
            return True
        except Exception:
            return False
    
    def toggle_indicator(self, indicator_name: str) -> bool:
        """Toggle an indicator on/off."""
        try:
            indicator_toggle = self.driver.find_element(
                By.CSS_SELECTOR, f".indicator-toggle[data-indicator='{indicator_name}']"
            )
            indicator_toggle.click()
            time.sleep(1)  # Wait for chart update
            return True
        except Exception:
            return False
    
    def zoom_in(self) -> bool:
        """Zoom in on the chart."""
        try:
            zoom_button = self.driver.find_element(*self.ZOOM_IN_BUTTON)
            zoom_button.click()
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def zoom_out(self) -> bool:
        """Zoom out on the chart."""
        try:
            zoom_button = self.driver.find_element(*self.ZOOM_OUT_BUTTON)
            zoom_button.click()
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def reset_zoom(self) -> bool:
        """Reset chart zoom to default."""
        try:
            reset_button = self.driver.find_element(*self.RESET_ZOOM_BUTTON)
            reset_button.click()
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def wait_for_data_update(self, timeout: int = 10) -> bool:
        """Wait for real-time data to update."""
        try:
            # Get initial timestamp
            initial_update = self.driver.find_element(*self.LAST_UPDATE).text
            
            # Wait for timestamp to change
            start_time = time.time()
            while time.time() - start_time < timeout:
                current_update = self.driver.find_element(*self.LAST_UPDATE).text
                if current_update != initial_update:
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
                "height": canvas.size['height']
            }
        except Exception:
            return {"width": 0, "height": 0}
    
    def is_chart_interactive(self) -> bool:
        """Test if chart responds to interactions."""
        try:
            # Try to interact with chart (hover, click)
            canvas = self.driver.find_element(*self.CHART_CANVAS)
            
            # Move mouse to center of chart
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element(canvas).perform()
            
            time.sleep(1)
            return True
        except Exception:
            return False
    
    def _extract_numeric_value(self, text: str) -> float:
        """Extract numeric value from text string."""
        import re
        # Remove currency symbols and extract number
        cleaned = re.sub(r'[^\d.-]', '', text)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def capture_dashboard_state(self) -> Dict[str, Any]:
        """Capture complete dashboard state for debugging."""
        return {
            "strategy_status": self.get_strategy_status(),
            "broker_status": self.get_broker_status(),
            "account_balance": self.get_account_balance(),
            "pnl": self.get_pnl_display(),
            "trade_count": self.get_trade_count(),
            "current_price": self.get_current_price(),
            "price_change": self.get_price_change(),
            "connection_status": self.get_connection_status(),
            "trading_signals": self.get_trading_signals(),
            "chart_dimensions": self.get_chart_dimensions(),
            "chart_interactive": self.is_chart_interactive(),
            "timestamp": time.time()
        } 