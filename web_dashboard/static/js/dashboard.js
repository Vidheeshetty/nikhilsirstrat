/**
 * Trading Dashboard - Main Application
 * Orchestrates all modules and handles UI interactions
 */

import DataService from './modules/DataService.js';
import ChartManager from './modules/ChartManager.js';
import IndicatorManager from './modules/IndicatorManager.js';
import TimeframeManager from './modules/TimeframeManager.js';

class TradingDashboard {
    constructor() {
        this.dataService = new DataService();
        this.chartManager = null;
        this.indicatorManager = null;
        this.timeframeManager = null;
        this.updateInterval = null;
        this.settings = {
            updateFrequency: 1000,
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
            
            // Initialize UI components
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
        
        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
        
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
        document.getElementById('fit-content-btn')?.addEventListener('click', () => {
            this.chartManager.fitContent();
        });
        
        document.getElementById('screenshot-btn')?.addEventListener('click', () => {
            this.takeScreenshot();
        });
        
        document.getElementById('fullscreen-btn')?.addEventListener('click', () => {
            this.toggleFullscreen();
        });
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        try {
            console.log('📊 Loading initial data...');
            
            // Load historical chart data
            await this.chartManager.loadHistoricalData();
            
            // Initialize indicators
            await this.indicatorManager.initializeIndicators();
            
            // Setup indicator controls
            this.setupIndicatorControls();
            
            // Load current metrics
            await this.updateMetrics();
            
            console.log('✅ Initial data loaded');
            
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            this.showError('Failed to load chart data');
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
        this.updateIndicatorValues();
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
        
        // Update metrics
        this.updateMetrics();
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        // Start indicator updates
        this.indicatorManager.startRealTimeUpdates();
        
        // Update metrics periodically
        this.updateInterval = setInterval(() => {
            this.updateMetrics();
        }, this.settings.updateFrequency);
        
        console.log('🔄 Started real-time updates');
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
            
            // Fetch additional metrics from API
            const response = await fetch('/api/indicators');
            if (response.ok) {
                const data = await response.json();
                
                // Update executed trades
                const tradesEl = document.getElementById('executed-trades');
                if (tradesEl) {
                    tradesEl.textContent = data.executed_trades || 0;
                }
                
                // Update total signals
                const signalsEl = document.getElementById('total-signals');
                if (signalsEl) {
                    signalsEl.textContent = data.total_signals || 0;
                }
                
                // Update fractal status
                const fractalStatusEl = document.getElementById('fractal-status');
                if (fractalStatusEl) {
                    fractalStatusEl.textContent = data.fractal_status || '--';
                }
                
                // Update strategy status
                const strategyStatusEl = document.getElementById('strategy-status-value');
                if (strategyStatusEl) {
                    strategyStatusEl.textContent = data.strategy_status || 'Running';
                }
            }
            
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
        
        settingsBtn?.addEventListener('click', () => {
            modal.style.display = 'flex';
            this.loadSettings();
        });
        
        closeBtn?.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        saveBtn?.addEventListener('click', () => {
            this.saveSettings();
            modal.style.display = 'none';
        });
        
        resetBtn?.addEventListener('click', () => {
            this.resetSettings();
        });
        
        // Close modal on outside click
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
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
                    this.chartManager.fitContent();
                    break;
                case 's':
                    e.preventDefault();
                    this.takeScreenshot();
                    break;
                case 'Escape':
                    const modal = document.getElementById('settings-modal');
                    if (modal.style.display === 'flex') {
                        modal.style.display = 'none';
                    }
                    break;
            }
        });
        
        // Setup timeframe shortcuts
        this.timeframeManager.setupKeyboardShortcuts();
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
        document.getElementById('update-frequency').value = this.settings.updateFrequency;
        document.getElementById('chart-theme').value = this.settings.chartTheme;
        document.getElementById('auto-fit-chart').checked = this.settings.autoFitChart;
    }

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        this.settings.updateFrequency = parseInt(document.getElementById('update-frequency').value);
        this.settings.chartTheme = document.getElementById('chart-theme').value;
        this.settings.autoFitChart = document.getElementById('auto-fit-chart').checked;
        
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
            updateFrequency: 1000,
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
        // Update update interval
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = setInterval(() => {
                this.updateMetrics();
            }, this.settings.updateFrequency);
        }
        
        // Apply chart theme (if implemented)
        // this.chartManager.setTheme(this.settings.chartTheme);
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
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        this.indicatorManager?.stopRealTimeUpdates();
        this.dataService?.disconnect();
        this.chartManager?.destroy();
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