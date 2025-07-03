/**
 * TimeframeManager - Manages multiple timeframes for chart display
 * Handles timeframe switching and data synchronization
 */
class TimeframeManager {
    constructor(chartManager, indicatorManager, dataService) {
        this.chartManager = chartManager;
        this.indicatorManager = indicatorManager;
        this.dataService = dataService;
        this.currentTimeframe = '1m';
        this.availableTimeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d'];
        this.timeframeData = new Map();
    }

    /**
     * Initialize timeframe manager
     */
    init() {
        this.setupTimeframeButtons();
        this.setActiveTimeframe(this.currentTimeframe);
        console.log('✅ TimeframeManager initialized');
    }

    /**
     * Setup timeframe buttons in UI
     */
    setupTimeframeButtons() {
        const container = document.getElementById('timeframe-buttons');
        if (!container) {
            console.warn('⚠️ Timeframe buttons container not found');
            return;
        }

        container.innerHTML = '';

        this.availableTimeframes.forEach(timeframe => {
            const button = document.createElement('button');
            button.className = 'timeframe-btn';
            button.textContent = timeframe;
            button.dataset.timeframe = timeframe;
            
            button.addEventListener('click', () => {
                this.switchTimeframe(timeframe);
            });

            container.appendChild(button);
        });
    }

    /**
     * Switch to a different timeframe
     */
    async switchTimeframe(timeframe) {
        if (timeframe === this.currentTimeframe) {
            return;
        }

        console.log(`📅 Switching timeframe: ${this.currentTimeframe} → ${timeframe}`);

        try {
            // Show loading state
            this.showLoadingState(true);

            // Update current timeframe
            const previousTimeframe = this.currentTimeframe;
            this.currentTimeframe = timeframe;

            // Update UI
            this.setActiveTimeframe(timeframe);

            // Update chart
            await this.chartManager.updateTimeframe(timeframe);

            // Update indicators
            await this.indicatorManager.reloadIndicators(timeframe);

            console.log(`✅ Successfully switched to ${timeframe}`);

        } catch (error) {
            console.error(`❌ Failed to switch timeframe to ${timeframe}:`, error);
            
            // Revert to previous timeframe on error
            this.currentTimeframe = previousTimeframe;
            this.setActiveTimeframe(previousTimeframe);
            
            // Show error message
            this.showErrorMessage(`Failed to load ${timeframe} data`);
        } finally {
            this.showLoadingState(false);
        }
    }

    /**
     * Set active timeframe in UI
     */
    setActiveTimeframe(timeframe) {
        const buttons = document.querySelectorAll('.timeframe-btn');
        buttons.forEach(button => {
            if (button.dataset.timeframe === timeframe) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });

        // Update timeframe display
        const display = document.getElementById('current-timeframe');
        if (display) {
            display.textContent = timeframe;
        }
    }

    /**
     * Show loading state
     */
    showLoadingState(loading) {
        const loader = document.getElementById('chart-loader');
        const chart = document.getElementById('trading-chart');

        if (loader && chart) {
            if (loading) {
                loader.style.display = 'flex';
                chart.style.opacity = '0.5';
            } else {
                loader.style.display = 'none';
                chart.style.opacity = '1';
            }
        }

        // Disable timeframe buttons during loading
        const buttons = document.querySelectorAll('.timeframe-btn');
        buttons.forEach(button => {
            button.disabled = loading;
        });
    }

    /**
     * Show error message
     */
    showErrorMessage(message) {
        const errorContainer = document.getElementById('error-message');
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
            
            // Hide error after 5 seconds
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Get current timeframe
     */
    getCurrentTimeframe() {
        return this.currentTimeframe;
    }

    /**
     * Get available timeframes
     */
    getAvailableTimeframes() {
        return this.availableTimeframes;
    }

    /**
     * Setup keyboard shortcuts for timeframe switching
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Only handle if no input is focused
            if (document.activeElement.tagName === 'INPUT') return;

            const key = event.key;
            const shortcuts = {
                '1': '1m',
                '3': '3m',
                '5': '5m',
                'q': '15m',
                'w': '30m',
                'h': '1h',
                'd': '1d'
            };

            if (shortcuts[key]) {
                event.preventDefault();
                this.switchTimeframe(shortcuts[key]);
            }
        });

        console.log('⌨️ Keyboard shortcuts enabled for timeframes');
    }
}

export default TimeframeManager; 