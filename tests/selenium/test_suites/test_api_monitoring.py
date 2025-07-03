"""
API Monitoring Tests for Trading Dashboard.

Tests to detect and prevent:
- Excessive API polling (indicators, status, logs)
- API call loops and infinite requests
- Performance degradation from API abuse
- Memory leaks from unclosed connections
"""

import pytest
import time
import json
import requests
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

@pytest.mark.selenium
@pytest.mark.prod
@pytest.mark.performance
class TestAPIMonitoring:
    """Production tests for API call monitoring and abuse detection."""
    
    def test_indicators_api_not_excessive(self, browser, test_config):
        """Test that /api/indicators endpoint is not called excessively."""
        # Navigate to chart dashboard
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for page to load
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Monitor for 30 seconds by checking server access logs
        monitoring_duration = 30
        start_time = time.time()
        
        # Collect API call data by monitoring the dashboard behavior
        # We'll use JavaScript to track fetch calls
        browser.execute_script("""
            window.apiCallCount = {
                indicators: 0,
                total: 0,
                calls: []
            };
            
            // Override fetch to count calls
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                if (url.includes('/api/')) {
                    window.apiCallCount.total++;
                    window.apiCallCount.calls.push({
                        url: url,
                        timestamp: Date.now()
                    });
                    
                    if (url.includes('/api/indicators')) {
                        window.apiCallCount.indicators++;
                    }
                }
                return originalFetch.apply(this, arguments);
            };
        """)
        
        # Wait and monitor
        time.sleep(monitoring_duration)
        
        # Get the call statistics
        api_stats = browser.execute_script("""
            return window.apiCallCount || {indicators: 0, total: 0, calls: []};
        """)
        
        indicators_count = api_stats.get('indicators', 0)
        total_calls = api_stats.get('total', 0)
        all_calls = api_stats.get('calls', [])
        
        indicators_rate = indicators_count / monitoring_duration
        
        # Critical thresholds
        MAX_INDICATORS_CALLS_PER_30_SEC = 20  # Should not exceed 20 calls in 30 seconds
        MAX_INDICATORS_RATE = 1.0  # Should not exceed 1 call per second
        
        # Log statistics for debugging
        print(f"API Call Statistics ({monitoring_duration}s monitoring):")
        print(f"Total API calls: {total_calls}")
        print(f"Indicators calls: {indicators_count} (rate: {indicators_rate:.2f}/sec)")
        
        # Group calls by endpoint for detailed analysis
        calls_by_endpoint = defaultdict(int)
        for call in all_calls:
            endpoint = call['url'].split('/')[-1].split('?')[0]
            calls_by_endpoint[endpoint] += 1
        
        for endpoint, count in calls_by_endpoint.items():
            endpoint_rate = count / monitoring_duration
            print(f"  {endpoint}: {count} calls ({endpoint_rate:.2f}/sec)")
        
        # Assertions
        assert indicators_count <= MAX_INDICATORS_CALLS_PER_30_SEC, \
            f"Indicators API called {indicators_count} times in {monitoring_duration}s (max: {MAX_INDICATORS_CALLS_PER_30_SEC})"
        
        assert indicators_rate <= MAX_INDICATORS_RATE, \
            f"Indicators API rate {indicators_rate:.2f}/sec exceeds limit {MAX_INDICATORS_RATE}/sec"
        
        # Check for polling loops by analyzing call patterns
        if indicators_count > 5:
            indicator_calls = [call for call in all_calls if '/api/indicators' in call['url']]
            timestamps = [call['timestamp'] for call in indicator_calls]
            
            if len(timestamps) > 1:
                intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
                avg_interval = sum(intervals) / len(intervals)
                
                # If calls are too frequent and regular, it's likely a polling loop
                if avg_interval < 2000:  # Less than 2 seconds between calls
                    regular_intervals = sum(1 for interval in intervals if abs(interval - avg_interval) < 500)
                    if regular_intervals > len(intervals) * 0.8:  # 80% of intervals are regular
                        assert False, f"Detected polling loop: {indicators_count} calls with {avg_interval:.0f}ms average interval"
    
    def test_dashboard_load_without_excessive_calls(self, browser, test_config):
        """Test that dashboard initial load doesn't make excessive API calls."""
        # Set up call tracking before navigation
        browser.execute_script("""
            window.loadCallCount = {
                indicators: 0,
                total: 0,
                calls: [],
                startTime: Date.now()
            };
            
            // Override fetch to count calls during load
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                if (url.includes('/api/')) {
                    window.loadCallCount.total++;
                    window.loadCallCount.calls.push({
                        url: url,
                        timestamp: Date.now(),
                        relativeTime: Date.now() - window.loadCallCount.startTime
                    });
                    
                    if (url.includes('/api/indicators')) {
                        window.loadCallCount.indicators++;
                    }
                }
                return originalFetch.apply(this, arguments);
            };
        """)
        
        # Navigate to chart dashboard
        start_time = time.time()
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for page to load completely
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait for initial loading to stabilize
        time.sleep(10)
        load_time = time.time() - start_time
        
        # Get loading statistics
        load_stats = browser.execute_script("""
            return window.loadCallCount || {indicators: 0, total: 0, calls: []};
        """)
        
        indicators_count = load_stats.get('indicators', 0)
        total_calls = load_stats.get('total', 0)
        all_calls = load_stats.get('calls', [])
        
        # Group calls by endpoint
        calls_by_endpoint = defaultdict(int)
        for call in all_calls:
            endpoint = call['url'].split('/')[-1].split('?')[0]
            calls_by_endpoint[endpoint] += 1
        
        # Thresholds for loading
        MAX_TOTAL_CALLS_ON_LOAD = 15  # Should not exceed 15 API calls during load
        MAX_INDICATORS_CALLS_ON_LOAD = 5  # Should not exceed 5 indicator calls during load
        
        # Log statistics
        print(f"Dashboard Load Statistics ({load_time:.1f}s load time):")
        print(f"Total API calls during load: {total_calls}")
        print(f"Indicators calls during load: {indicators_count}")
        
        for endpoint, count in calls_by_endpoint.items():
            print(f"  {endpoint}: {count} calls")
        
        # Assertions
        assert total_calls <= MAX_TOTAL_CALLS_ON_LOAD, \
            f"Dashboard load made {total_calls} API calls (max: {MAX_TOTAL_CALLS_ON_LOAD})"
        
        assert indicators_count <= MAX_INDICATORS_CALLS_ON_LOAD, \
            f"Dashboard load made {indicators_count} indicator calls (max: {MAX_INDICATORS_CALLS_ON_LOAD})"
        
        # Check for rapid duplicate calls during load
        rapid_call_endpoints = []
        for call in all_calls:
            endpoint = call['url'].split('/')[-1].split('?')[0]
            if call['relativeTime'] < 5000:  # Within first 5 seconds
                rapid_call_endpoints.append(endpoint)
        
        # Count rapid calls per endpoint
        rapid_counts = Counter(rapid_call_endpoints)
        for endpoint, count in rapid_counts.items():
            if count > 3:  # More than 3 calls to same endpoint in first 5 seconds
                assert False, f"Endpoint {endpoint} called {count} times rapidly during load"
    
    def test_api_endpoints_respond_efficiently(self, test_config):
        """Test that API endpoints respond within acceptable time limits."""
        base_url = test_config['dashboard_url']
        
        # Test critical endpoints
        endpoints_to_test = [
            ('/api/status', 2.0),  # Should respond within 2 seconds
            ('/api/indicators', 3.0),  # Should respond within 3 seconds
            ('/api/chart/data?symbol=GOLDGUINEA&timeframe=1m&bars=10', 5.0),  # Should respond within 5 seconds
        ]
        
        response_times = {}
        
        for endpoint, max_time in endpoints_to_test:
            url = f"{base_url}{endpoint}"
            
            # Test response time
            start_time = time.time()
            try:
                response = requests.get(url, timeout=max_time + 1)
                response_time = time.time() - start_time
                
                response_times[endpoint] = {
                    'time': response_time,
                    'status': response.status_code,
                    'success': response.status_code == 200
                }
                
                # Log response time
                print(f"{endpoint}: {response_time:.3f}s (status: {response.status_code})")
                
                # Assert response time and status
                assert response.status_code == 200, f"Endpoint {endpoint} returned status {response.status_code}"
                assert response_time <= max_time, f"Endpoint {endpoint} took {response_time:.3f}s (max: {max_time}s)"
                
            except requests.Timeout:
                assert False, f"Endpoint {endpoint} timed out (>{max_time}s)"
            except requests.RequestException as e:
                assert False, f"Endpoint {endpoint} failed: {str(e)}"
        
        # Overall performance check
        avg_response_time = sum(rt['time'] for rt in response_times.values()) / len(response_times)
        print(f"Average API response time: {avg_response_time:.3f}s")
        
        assert avg_response_time <= 3.0, f"Average API response time {avg_response_time:.3f}s too slow (max: 3.0s)"

@pytest.mark.selenium
@pytest.mark.dev
@pytest.mark.debug
class TestAPIDebugging:
    """Debug tests for API call analysis and troubleshooting."""
    
    def test_capture_api_call_patterns(self, browser, test_config):
        """Capture and analyze API call patterns for debugging."""
        # Set up comprehensive call tracking
        browser.execute_script("""
            window.debugCallTracker = {
                calls: [],
                startTime: Date.now(),
                intervals: {}
            };
            
            // Override fetch to track all calls
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                if (url.includes('/api/')) {
                    const now = Date.now();
                    window.debugCallTracker.calls.push({
                        url: url,
                        timestamp: now,
                        relativeTime: now - window.debugCallTracker.startTime
                    });
                }
                return originalFetch.apply(this, arguments);
            };
        """)
        
        # Navigate to dashboard
        browser.get(f"{test_config['dashboard_url']}/chart")
        
        # Wait for initial load
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Monitor for extended period
        monitoring_duration = 15
        time.sleep(monitoring_duration)
        
        # Collect debug information
        debug_data = browser.execute_script("""
            const tracker = window.debugCallTracker;
            const calls = tracker.calls || [];
            
            // Group calls by endpoint
            const callsByEndpoint = {};
            calls.forEach(call => {
                const endpoint = call.url.split('/').pop().split('?')[0];
                if (!callsByEndpoint[endpoint]) {
                    callsByEndpoint[endpoint] = [];
                }
                callsByEndpoint[endpoint].push(call);
            });
            
            // Calculate patterns
            const patterns = {};
            Object.keys(callsByEndpoint).forEach(endpoint => {
                const endpointCalls = callsByEndpoint[endpoint];
                const timestamps = endpointCalls.map(c => c.timestamp);
                const intervals = [];
                
                for (let i = 1; i < timestamps.length; i++) {
                    intervals.push(timestamps[i] - timestamps[i-1]);
                }
                
                patterns[endpoint] = {
                    count: endpointCalls.length,
                    rate: endpointCalls.length / (Date.now() - tracker.startTime) * 1000,
                    avgInterval: intervals.length > 0 ? intervals.reduce((a, b) => a + b, 0) / intervals.length : 0,
                    minInterval: intervals.length > 0 ? Math.min(...intervals) : 0,
                    maxInterval: intervals.length > 0 ? Math.max(...intervals) : 0
                };
            });
            
            return {
                totalCalls: calls.length,
                totalDuration: Date.now() - tracker.startTime,
                patterns: patterns,
                allCalls: calls
            };
        """)
        
        # Analyze and save debug information
        debug_info = {
            'total_duration': debug_data.get('totalDuration', 0) / 1000,
            'total_calls': debug_data.get('totalCalls', 0),
            'call_patterns': debug_data.get('patterns', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        # Save debug information
        debug_dir = Path("testlogs/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"api_debug_{timestamp}.json"
        
        with open(debug_file, "w") as f:
            json.dump(debug_info, f, indent=2, default=str)
        
        print(f"API Debug Information saved to: {debug_file}")
        print(f"Total monitoring duration: {debug_info['total_duration']:.1f}s")
        print(f"Total API calls: {debug_info['total_calls']}")
        
        # Print call patterns
        print("\nAPI Call Patterns:")
        for endpoint, pattern in debug_info['call_patterns'].items():
            print(f"  {endpoint}:")
            print(f"    Count: {pattern['count']}")
            print(f"    Rate: {pattern['rate']:.2f}/sec")
            if pattern['avgInterval'] > 0:
                print(f"    Avg Interval: {pattern['avgInterval']:.0f}ms")
                print(f"    Min Interval: {pattern['minInterval']:.0f}ms")
        
        # Flag potential issues
        issues = []
        for endpoint, pattern in debug_info['call_patterns'].items():
            if pattern['rate'] > 1.0:  # More than 1 call per second
                issues.append(f"High call rate for {endpoint}: {pattern['rate']:.2f}/sec")
            
            if pattern['minInterval'] > 0 and pattern['minInterval'] < 500:  # Calls less than 500ms apart
                issues.append(f"Rapid calls for {endpoint}: min interval {pattern['minInterval']:.0f}ms")
            
            if pattern['count'] > 20:  # More than 20 calls in monitoring period
                issues.append(f"High call count for {endpoint}: {pattern['count']} calls")
        
        if issues:
            print("\nPotential Issues Detected:")
            for issue in issues:
                print(f"  - {issue}")
        
        # This is a debug test - it captures information but doesn't fail
        assert True, "API debug information captured successfully" 