/**
 * Trading Dashboard - Main Application
 * Orchestrates all modules and handles UI interactions
 */

import DataService from './modules/DataService.js?v=1.6';
import ChartManager from './modules/ChartManager.js?v=1.6';
import IndicatorManager from './modules/IndicatorManager.js?v=1.6';
import TimeframeManager from './modules/TimeframeManager.js?v=1.6';

class TradingDashboard {
    constructor() {
        this.dataService = new DataService();
        this.chartManager = null;
        this.indicatorManager = null;
        this.timeframeManager = null;
        this.updateInterval = null;
        this.settings = {
            updateFrequency: 5000,
            chartTheme: 'dark',
            autoFitChart: true
        };
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        try {
            console.log('🚀 Initializing Trading Dashboard...');
            
            // Initialize UI components (without keyboard shortcuts)
            this.initUI();
            
            // Initialize chart manager
            this.chartManager = new ChartManager('trading-chart', this.dataService);
            this.chartManager.initChart();
            
            // Initialize indicator manager
            this.indicatorManager = new IndicatorManager(this.chartManager, this.dataService);
            
            // Initialize timeframe manager
            this.timeframeManager = new TimeframeManager(
                this.chartManager,
                this.indicatorManager,
                this.dataService
            );
            this.timeframeManager.init();
            
            // Initialize indicators
            await this.indicatorManager.initializeIndicators();
            
            // Initialize indicator button states
            this.initializeIndicatorStates();
            
            // Setup keyboard shortcuts (after all managers are initialized)
            this.setupKeyboardShortcuts();
            
            // Connect to WebSocket
            await this.dataService.connectWebSocket();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            // Start real-time updates
            this.startRealTimeUpdates();
            
            console.log('✅ Trading Dashboard initialized successfully');
            
        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            this.showError('Failed to initialize dashboard');
        }
    }

    /**
     * Initialize UI components
     */
    initUI() {
        // Update current time
        this.updateCurrentTime();
        setInterval(() => this.updateCurrentTime(), 1000);
        
        // Setup modal handlers
        this.setupModalHandlers();
        
        // Note: keyboard shortcuts setup moved to after managers are initialized
        
        // Update connection status
        this.updateConnectionStatus('connecting');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // WebSocket events
        this.dataService.subscribe('connection', (data) => {
            this.handleConnectionStatus(data);
        });
        
        this.dataService.subscribe('bar_update', (data) => {
            this.handleBarUpdate(data);
        });
        
        this.dataService.subscribe('indicator_update', (data) => {
            this.handleIndicatorUpdate(data);
        });
        
        this.dataService.subscribe('signal_generated', (data) => {
            this.handleSignalGenerated(data);
        });
        
        this.dataService.subscribe('trade_executed', (data) => {
            this.handleTradeExecuted(data);
        });
        
        // Chart control buttons
        const fitContentBtn = document.getElementById('fit-content-btn');
        if (fitContentBtn) {
            fitContentBtn.addEventListener('click', () => {
                this.chartManager.fitContent();
            });
        }
        
        const screenshotBtn = document.getElementById('screenshot-btn');
        if (screenshotBtn) {
            screenshotBtn.addEventListener('click', () => {
                this.takeScreenshot();
            });
        }
        
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                this.toggleFullscreen();
            });
        }
        
        // Clear cache button
        const clearCacheBtn = document.getElementById('clear-cache-btn');
        if (clearCacheBtn) {
            clearCacheBtn.addEventListener('click', () => {
                this.clearBrowserCache();
            });
        }
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            console.log('📊 Loading initial data...');
            
            // Load historical chart data
            await this.chartManager.loadHistoricalData();
            
            // Initialize indicators (this will load and display them)
            await this.indicatorManager.initializeIndicators();
            
            // Setup indicator controls
            this.setupIndicatorControls();
            
            // Load current metrics (but don't reload indicators)
            await this.updateMetricsOnly();
            
            console.log('✅ Initial data loaded');
            
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            this.showError('Failed to load chart data');
        }
    }

    /**
     * Update metrics without reloading indicators
     */
    async updateMetricsOnly() {
        try {
            // Get current indicator values from chart manager (no API call)
            const indicatorValues = this.indicatorManager.getCurrentValues();
            
            // Update SMA values if available
            if (indicatorValues.sma_5) {
                const sma5El = document.getElementById('sma-5-value');
                if (sma5El) {
                    sma5El.textContent = `₹${indicatorValues.sma_5.value.toFixed(2)}`;
                }
            }
            
            if (indicatorValues.sma_200) {
                const sma200El = document.getElementById('sma-200-value');
                if (sma200El) {
                    sma200El.textContent = `₹${indicatorValues.sma_200.value.toFixed(2)}`;
                }
            }
            
            // Update trend status
            const trendStatus = this.indicatorManager.getTrendStatus();
            const trendEl = document.getElementById('sma-trend');
            if (trendEl) {
                trendEl.textContent = trendStatus.trend;
                trendEl.className = `metric-value ${trendStatus.trend.toLowerCase()}`;
            }
            
            // ✅ REMOVED API CALL - All metrics now come via WebSocket
            console.log('📊 Metrics updated from local data (no API call)');
            
        } catch (error) {
            console.error('❌ Error updating metrics:', error);
        }
    }

    /**
     * Setup indicator controls in UI
     */
    setupIndicatorControls() {
        const container = document.getElementById('indicator-controls');
        if (!container) return;
        
        const indicators = this.indicatorManager.getIndicatorConfig();
        container.innerHTML = '';
        
        indicators.forEach(indicator => {
            const control = document.createElement('div');
            control.className = 'indicator-control';
            control.innerHTML = `
                <span class="indicator-name" style="color: ${indicator.color}">
                    ${indicator.title}
                </span>
                <div class="indicator-toggle ${indicator.visible ? 'active' : ''}" 
                     data-indicator="${indicator.id}">
                </div>
            `;
            
            const toggle = control.querySelector('.indicator-toggle');
            toggle.addEventListener('click', () => {
                const isVisible = this.indicatorManager.toggleIndicator(indicator.id);
                toggle.classList.toggle('active', isVisible);
            });
            
            container.appendChild(control);
        });
    }

    /**
     * Handle connection status changes
     */
    handleConnectionStatus(data) {
        this.updateConnectionStatus(data.status);
        
        if (data.status === 'connected') {
            this.addActivity('WebSocket connected', 'Connected to real-time data feed');
        } else if (data.status === 'disconnected') {
            this.addActivity('WebSocket disconnected', 'Lost connection to data feed');
        }
    }

    /**
     * Handle bar updates
     */
    handleBarUpdate(data) {
        if (data.data && data.data.bar) {
            this.chartManager.updateLastBar(data.data.bar);
            this.updateCurrentPrice(data.data.bar.close);
        }
    }

    /**
     * Handle indicator updates
     */
    handleIndicatorUpdate(data) {
        this.indicatorManager.handleIndicatorUpdate(data);
        
        // Update all UI elements from WebSocket data
        if (data.data) {
            const indicators = data.data;
            
            // Update price and trend
            if (indicators.current_price) {
                const priceEl = document.getElementById('current-price');
                if (priceEl) {
                    priceEl.textContent = `₹${indicators.current_price.toFixed(2)}`;
                }
            }
            
            // Update SMA values
            if (indicators.sma_short) {
                const sma5El = document.getElementById('sma-5-value');
                if (sma5El) {
                    sma5El.textContent = `₹${indicators.sma_short.toFixed(2)}`;
                }
            }
            
            if (indicators.sma_long) {
                const sma200El = document.getElementById('sma-200-value');
                if (sma200El) {
                    sma200El.textContent = `₹${indicators.sma_long.toFixed(2)}`;
                }
            }
            
            // Update trend
            if (indicators.sma_trend) {
                const trendEl = document.getElementById('sma-trend');
                if (trendEl) {
                    trendEl.textContent = indicators.sma_trend;
                    trendEl.className = `metric-value ${indicators.sma_trend.toLowerCase()}`;
                }
            }
            
            // Update trading metrics (handle both field names for compatibility)
            if (indicators.total_trades !== undefined || indicators.executed_trades !== undefined) {
                const tradesEl = document.getElementById('executed-trades');
                if (tradesEl) {
                    tradesEl.textContent = indicators.executed_trades || indicators.total_trades || 0;
                }
            }
            
            if (indicators.total_signals !== undefined) {
                const signalsEl = document.getElementById('total-signals');
                if (signalsEl) {
                    signalsEl.textContent = indicators.total_signals;
                }
            }
            
            if (indicators.fractal_status) {
                const fractalEl = document.getElementById('fractal-status');
                if (fractalEl) {
                    fractalEl.textContent = indicators.fractal_status;
                }
            }
            
            if (indicators.no_signal_reason) {
                const reasonEl = document.getElementById('no-signal-reason');
                if (reasonEl) {
                    reasonEl.textContent = indicators.no_signal_reason;
                }
            }
            
            // Update strategy status
            if (indicators.strategy_status) {
                const strategyStatusEl = document.getElementById('strategy-status-value');
                if (strategyStatusEl) {
                    strategyStatusEl.textContent = indicators.strategy_status;
                }
            }
        }
    }

    /**
     * Handle signal generation
     */
    handleSignalGenerated(data) {
        const signal = data.data;
        this.addActivity(
            'Signal Generated',
            `${signal.direction} signal at ₹${signal.entry_price}`
        );
        
        // Update last signal display
        const lastSignalEl = document.getElementById('last-signal');
        if (lastSignalEl) {
            lastSignalEl.textContent = `${signal.direction} @ ₹${signal.entry_price}`;
            lastSignalEl.className = `status-value ${signal.direction.toLowerCase()}`;
        }
    }

    /**
     * Handle trade execution
     */
    handleTradeExecuted(data) {
        const trade = data.data;
        this.addActivity(
            'Trade Executed',
            `${trade.side} ${trade.quantity} @ ₹${trade.price}`
        );
        
        // Update metrics from WebSocket data only (no API call)
        this.updateMetricsOnly();
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        // CRITICAL: Always clear any existing interval first
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        // Start indicator updates
        this.indicatorManager.startRealTimeUpdates();
        
        // ✅ REMOVED POLLING - All data now comes via WebSocket
        // No more setInterval polling - WebSocket handles all real-time updates
        console.log('✅ Real-time updates started (WebSocket only - no polling)');
    }

    /**
     * Update current metrics
     */
    async updateMetrics() {
        try {
            // Get current indicator values
            const indicatorValues = this.indicatorManager.getCurrentValues();
            
            // Update SMA values
            if (indicatorValues.sma_5) {
                const sma5El = document.getElementById('sma-5-value');
                if (sma5El) {
                    sma5El.textContent = `₹${indicatorValues.sma_5.value.toFixed(2)}`;
                }
            }
            
            if (indicatorValues.sma_200) {
                const sma200El = document.getElementById('sma-200-value');
                if (sma200El) {
                    sma200El.textContent = `₹${indicatorValues.sma_200.value.toFixed(2)}`;
                }
            }
            
            // Update trend status
            const trendStatus = this.indicatorManager.getTrendStatus();
            const trendEl = document.getElementById('sma-trend');
            if (trendEl) {
                trendEl.textContent = trendStatus.trend;
                trendEl.className = `metric-value ${trendStatus.trend.toLowerCase()}`;
            }
            
            // ✅ REMOVED API POLLING - All metrics now come via WebSocket indicator_update events
            // The handleIndicatorUpdate() method handles all metrics updates in real-time
            console.log('📊 Metrics updated (WebSocket-only, no API calls)');
            
        } catch (error) {
            console.warn('⚠️ Failed to update metrics:', error);
        }
    }

    /**
     * Update current price display
     */
    updateCurrentPrice(price) {
        const priceEl = document.getElementById('current-price');
        if (priceEl) {
            priceEl.textContent = `₹${parseFloat(price).toFixed(2)}`;
        }
    }

    /**
     * Update indicator values display
     */
    updateIndicatorValues() {
        const values = this.indicatorManager.getCurrentValues();
        
        Object.entries(values).forEach(([id, data]) => {
            const element = document.getElementById(`${id}-value`);
            if (element && data.value !== undefined) {
                element.textContent = `₹${data.value.toFixed(2)}`;
            }
        });
    }

    /**
     * Update connection status in UI
     */
    updateConnectionStatus(status) {
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        
        if (indicator && text) {
            indicator.className = `status-indicator ${status}`;
            
            switch (status) {
                case 'connected':
                    text.textContent = 'Connected';
                    break;
                case 'connecting':
                    text.textContent = 'Connecting...';
                    break;
                case 'disconnected':
                    text.textContent = 'Disconnected';
                    break;
                case 'error':
                    text.textContent = 'Connection Error';
                    break;
            }
        }
    }

    /**
     * Update current time display
     */
    updateCurrentTime() {
        const timeEl = document.getElementById('current-time');
        if (timeEl) {
            timeEl.textContent = new Date().toLocaleTimeString();
        }
    }

    /**
     * Add activity to feed
     */
    addActivity(title, description) {
        const feed = document.getElementById('activity-feed');
        if (!feed) return;
        
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <div class="activity-time">${new Date().toLocaleTimeString()}</div>
            <div class="activity-text"><strong>${title}:</strong> ${description}</div>
        `;
        
        feed.insertBefore(item, feed.firstChild);
        
        // Keep only last 20 items
        while (feed.children.length > 20) {
            feed.removeChild(feed.lastChild);
        }
    }

    /**
     * Setup modal handlers
     */
    setupModalHandlers() {
        const settingsBtn = document.getElementById('settings-btn');
        const modal = document.getElementById('settings-modal');
        const closeBtn = document.getElementById('modal-close');
        const saveBtn = document.getElementById('save-settings');
        const resetBtn = document.getElementById('reset-settings');
        
        if (settingsBtn && modal) {
            settingsBtn.addEventListener('click', () => {
                modal.style.display = 'flex';
                this.loadSettings();
            });
        }
        
        if (closeBtn && modal) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }
        
        if (saveBtn && modal) {
            saveBtn.addEventListener('click', () => {
                this.saveSettings();
                modal.style.display = 'none';
            });
        }
        
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetSettings();
            });
        }
        
        // Close modal on outside click
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only handle if no input is focused
            if (document.activeElement.tagName === 'INPUT') return;
            
            switch (e.key) {
                case 'f':
                    e.preventDefault();
                    if (this.chartManager) {
                        this.chartManager.fitContent();
                    }
                    break;
                case 's':
                    e.preventDefault();
                    this.takeScreenshot();
                    break;
                case 'Escape':
                    const modal = document.getElementById('settings-modal');
                    if (modal && modal.style.display === 'flex') {
                        modal.style.display = 'none';
                    }
                    break;
            }
        });

        // Setup indicator collapse toggle
        const collapseBtn = document.getElementById('indicators-collapse-btn');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', this.toggleIndicatorPanel.bind(this));
        }

        // Setup individual indicator toggles
        this.setupIndicatorToggles();
    }

    /**
     * Setup individual indicator toggle buttons
     */
    setupIndicatorToggles() {
        const toggleButtons = document.querySelectorAll('.indicator-toggle');
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const indicatorId = button.getAttribute('data-indicator');
                this.toggleIndicator(indicatorId, button);
            });
        });
    }

    /**
     * Toggle indicator panel visibility
     */
    toggleIndicatorPanel() {
        const controls = document.getElementById('indicator-controls');
        const collapseBtn = document.getElementById('indicators-collapse-btn');
        const collapseIcon = collapseBtn.querySelector('.collapse-icon');
        
        if (controls.classList.contains('collapsed')) {
            controls.classList.remove('collapsed');
            collapseBtn.classList.remove('collapsed');
            collapseIcon.textContent = '▼';
        } else {
            controls.classList.add('collapsed');
            collapseBtn.classList.add('collapsed');
            collapseIcon.textContent = '▶';
        }
    }

    /**
     * Toggle individual indicator visibility
     */
    toggleIndicator(indicatorId, button) {
        if (!this.indicatorManager) return;
        
        const isVisible = this.indicatorManager.toggleIndicator(indicatorId);
        
        // Update button state
        if (isVisible) {
            button.classList.remove('hidden');
            button.classList.add('active');
            button.title = 'Hide indicator';
        } else {
            button.classList.add('hidden');
            button.classList.remove('active');
            button.title = 'Show indicator';
        }
        
        // Log activity
        this.addActivity(`${isVisible ? 'Showed' : 'Hid'} ${this.getIndicatorDisplayName(indicatorId)}`);
    }

    /**
     * Get human-readable indicator name
     */
    getIndicatorDisplayName(indicatorId) {
        const names = {
            'sma_5': '5-SMA',
            'sma_200': '200-SMA', 
            'fractals_high': 'High Fractals',
            'fractals_low': 'Low Fractals',
            'signals': 'Trade Signals'
        };
        return names[indicatorId] || indicatorId;
    }

    /**
     * Initialize indicator button states
     */
    initializeIndicatorStates() {
        if (!this.indicatorManager) return;
        
        const toggleButtons = document.querySelectorAll('.indicator-toggle');
        
        toggleButtons.forEach(button => {
            const indicatorId = button.getAttribute('data-indicator');
            const indicator = this.indicatorManager.indicators.get(indicatorId);
            
            if (indicator) {
                if (indicator.visible) {
                    button.classList.add('active');
                    button.classList.remove('hidden');
                    button.title = 'Hide indicator';
                } else {
                    button.classList.remove('active');
                    button.classList.add('hidden');
                    button.title = 'Show indicator';
                }
            }
        });
    }

    /**
     * Clear browser cache and reload page
     */
    clearBrowserCache() {
        // Show confirmation dialog
        const confirmed = confirm(
            'This will clear the browser cache and reload the page. ' +
            'This may help resolve dashboard loading issues. Continue?'
        );
        
        if (!confirmed) return;
        
        // Clear various browser caches
        try {
            // Clear localStorage
            localStorage.clear();
            
            // Clear sessionStorage
            sessionStorage.clear();
            
            // Clear IndexedDB (if supported)
            if ('indexedDB' in window) {
                indexedDB.databases().then(databases => {
                    databases.forEach(db => {
                        indexedDB.deleteDatabase(db.name);
                    });
                });
            }
            
            // Clear service worker caches (if supported)
            if ('caches' in window) {
                caches.keys().then(names => {
                    names.forEach(name => {
                        caches.delete(name);
                    });
                });
            }
            
            // Add timestamp to force reload
            const timestamp = Date.now();
            const url = new URL(window.location);
            url.searchParams.set('_cache_bust', timestamp);
            
            // Reload with cache busting
            window.location.href = url.toString();
            
        } catch (error) {
            console.error('Error clearing cache:', error);
            // Fallback: hard reload
            window.location.reload(true);
        }
    }

    /**
     * Take screenshot
     */
    takeScreenshot() {
        const screenshot = this.chartManager.takeScreenshot();
        if (screenshot) {
            const link = document.createElement('a');
            link.download = `chart-${Date.now()}.png`;
            link.href = screenshot.toDataURL();
            link.click();
            
            this.addActivity('Screenshot', 'Chart screenshot saved');
        }
    }

    /**
     * Toggle fullscreen
     */
    toggleFullscreen() {
        const chartContainer = document.querySelector('.chart-container');
        
        if (!document.fullscreenElement) {
            chartContainer.requestFullscreen().catch(err => {
                console.warn('Failed to enter fullscreen:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }

    /**
     * Load settings from localStorage
     */
    loadSettings() {
        const saved = localStorage.getItem('dashboard-settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
        }
        
        // Update form fields
        const updateFrequencyEl = document.getElementById('update-frequency');
        const chartThemeEl = document.getElementById('chart-theme');
        const autoFitChartEl = document.getElementById('auto-fit-chart');
        
        if (updateFrequencyEl) updateFrequencyEl.value = this.settings.updateFrequency;
        if (chartThemeEl) chartThemeEl.value = this.settings.chartTheme;
        if (autoFitChartEl) autoFitChartEl.checked = this.settings.autoFitChart;
    }

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        const updateFrequencyEl = document.getElementById('update-frequency');
        const chartThemeEl = document.getElementById('chart-theme');
        const autoFitChartEl = document.getElementById('auto-fit-chart');
        
        if (updateFrequencyEl) this.settings.updateFrequency = parseInt(updateFrequencyEl.value);
        if (chartThemeEl) this.settings.chartTheme = chartThemeEl.value;
        if (autoFitChartEl) this.settings.autoFitChart = autoFitChartEl.checked;
        
        localStorage.setItem('dashboard-settings', JSON.stringify(this.settings));
        
        // Apply settings
        this.applySettings();
        
        this.addActivity('Settings', 'Dashboard settings saved');
    }

    /**
     * Reset settings to defaults
     */
    resetSettings() {
        this.settings = {
            updateFrequency: 5000,
            chartTheme: 'dark',
            autoFitChart: true
        };
        
        localStorage.removeItem('dashboard-settings');
        this.loadSettings();
        this.applySettings();
        
        this.addActivity('Settings', 'Settings reset to defaults');
    }

    /**
     * Apply current settings
     */
    applySettings() {
        // ✅ REMOVED POLLING - No more interval creation
        // Settings now only affect chart appearance, not data polling
        
        // Apply chart theme
        if (this.chartManager) {
            this.chartManager.applyTheme(this.settings.chartTheme);
        }
        
        // Apply auto-fit setting
        if (this.settings.autoFitChart && this.chartManager) {
            this.chartManager.fitContent();
        }
        
        console.log('⚙️ Settings applied (no polling intervals created)');
        this.addActivity('Settings', 'Settings applied successfully');
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorEl = document.getElementById('error-message');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
            
            setTimeout(() => {
                errorEl.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Cleanup on page unload
     */
    cleanup() {
        console.log('🧹 Cleaning up dashboard...');
        
        // CRITICAL: Clear all intervals
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        if (this.indicatorManager) {
            this.indicatorManager.stopRealTimeUpdates();
        }
        
        if (this.dataService) {
            this.dataService.disconnect();
        }
        
        if (this.chartManager) {
            this.chartManager.destroy();
        }
        
        console.log('✅ Dashboard cleanup completed');
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    window.dashboard = new TradingDashboard();
    await window.dashboard.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.cleanup();
    }
});

export default TradingDashboard; 