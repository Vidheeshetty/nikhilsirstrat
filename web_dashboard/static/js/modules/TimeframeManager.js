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

            // Cache current timeframe data
            await this.cacheCurrentTimeframeData();

            // Update current timeframe
            const previousTimeframe = this.currentTimeframe;
            this.currentTimeframe = timeframe;

            // Update UI
            this.setActiveTimeframe(timeframe);

            // Load new timeframe data
            await this.loadTimeframeData(timeframe);

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
     * Cache current timeframe data
     */
    async cacheCurrentTimeframeData() {
        try {
            const cachedData = this.dataService.getCachedData(
                this.chartManager.symbol,
                this.currentTimeframe,
                500
            );

            if (cachedData) {
                this.timeframeData.set(this.currentTimeframe, {
                    bars: cachedData.bars,
                    indicators: this.indicatorManager.getCurrentValues(),
                    timestamp: Date.now()
                });
            }
        } catch (error) {
            console.warn('⚠️ Failed to cache timeframe data:', error);
        }
    }

    /**
     * Load timeframe data
     */
    async loadTimeframeData(timeframe) {
        // Check if we have cached data
        const cachedData = this.timeframeData.get(timeframe);
        const cacheAge = cachedData ? Date.now() - cachedData.timestamp : Infinity;
        const maxCacheAge = 5 * 60 * 1000; // 5 minutes

        if (cachedData && cacheAge < maxCacheAge) {
            console.log(`📦 Using cached data for ${timeframe}`);
            return cachedData;
        }

        // Load fresh data
        console.log(`🔄 Loading fresh data for ${timeframe}`);
        const data = await this.dataService.getHistoricalData(
            this.chartManager.symbol,
            timeframe,
            500
        );

        // Cache the new data
        if (data) {
            this.timeframeData.set(timeframe, {
                bars: data.bars,
                timestamp: Date.now()
            });
        }

        return data;
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
     * Get timeframe display name
     */
    getTimeframeDisplayName(timeframe) {
        const names = {
            '1m': '1 Minute',
            '3m': '3 Minutes',
            '5m': '5 Minutes',
            '15m': '15 Minutes',
            '30m': '30 Minutes',
            '1h': '1 Hour',
            '4h': '4 Hours',
            '1d': '1 Day'
        };
        return names[timeframe] || timeframe;
    }

    /**
     * Get timeframe color for UI
     */
    getTimeframeColor(timeframe) {
        const colors = {
            '1m': '#4CAF50',
            '3m': '#2196F3',
            '5m': '#FF9800',
            '15m': '#9C27B0',
            '30m': '#F44336',
            '1h': '#607D8B',
            '4h': '#795548',
            '1d': '#3F51B5'
        };
        return colors[timeframe] || '#666';
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
     * Preload adjacent timeframes
     */
    async preloadAdjacentTimeframes() {
        const currentIndex = this.availableTimeframes.indexOf(this.currentTimeframe);
        const adjacent = [];

        // Previous timeframe
        if (currentIndex > 0) {
            adjacent.push(this.availableTimeframes[currentIndex - 1]);
        }

        // Next timeframe
        if (currentIndex < this.availableTimeframes.length - 1) {
            adjacent.push(this.availableTimeframes[currentIndex + 1]);
        }

        // Load adjacent timeframes in background
        for (const timeframe of adjacent) {
            if (!this.timeframeData.has(timeframe)) {
                try {
                    await this.loadTimeframeData(timeframe);
                    console.log(`📦 Preloaded ${timeframe} data`);
                } catch (error) {
                    console.warn(`⚠️ Failed to preload ${timeframe}:`, error);
                }
            }
        }
    }

    /**
     * Clear cached data
     */
    clearCache() {
        this.timeframeData.clear();
        console.log('🧹 Cleared timeframe cache');
    }

    /**
     * Get cache statistics
     */
    getCacheStats() {
        const stats = {
            totalCached: this.timeframeData.size,
            timeframes: Array.from(this.timeframeData.keys()),
            totalSize: 0
        };

        this.timeframeData.forEach((data, timeframe) => {
            if (data.bars) {
                stats.totalSize += data.bars.length;
            }
        });

        return stats;
    }

    /**
     * Handle real-time timeframe updates
     */
    handleRealtimeUpdate(updateData) {
        const { timeframe, data } = updateData;
        
        // Only update if it's the current timeframe
        if (timeframe === this.currentTimeframe) {
            // Update cached data
            const cachedData = this.timeframeData.get(timeframe);
            if (cachedData && cachedData.bars) {
                const lastBar = cachedData.bars[cachedData.bars.length - 1];
                if (lastBar && lastBar.timestamp === data.timestamp) {
                    // Update existing bar
                    cachedData.bars[cachedData.bars.length - 1] = data;
                } else {
                    // Add new bar
                    cachedData.bars.push(data);
                }
            }
        }
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