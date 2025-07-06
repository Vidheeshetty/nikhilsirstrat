/**
 * ChartManager - Manages TradingView Lightweight Charts
 * Handles chart creation, data updates, and user interactions
 */
class ChartManager {
    constructor(containerId, dataService) {
        this.containerId = containerId;
        this.dataService = dataService;
        this.chart = null;
        this.candlestickSeries = null;
        this.indicators = new Map();
        this.markers = new Map(); // Store markers by type
        this.markerSeries = new Map(); // Store marker series by ID
        this.currentTimeframe = '1m';
        this.symbol = 'GOLDGUINEA';
        this.indicatorVisibility = new Map(); // Track indicator visibility states
        
        // Chart configuration with enhanced features
        this.chartOptions = {
            layout: {
                background: { color: '#1a1a1a' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: '#2a2a2a' },
                horzLines: { color: '#2a2a2a' },
            },
            crosshair: {
                mode: 1, // Normal crosshair mode
            },
            rightPriceScale: {
                borderColor: '#485158',
                visible: true,
                scaleMargins: {
                    top: 0.1,    // 10% margin at top for vertical zoom
                    bottom: 0.1, // 10% margin at bottom for vertical zoom
                },
                autoScale: true,
                entireTextOnly: false,
                borderVisible: true,
                ticksVisible: true,
                alignLabels: true,
            },
            leftPriceScale: {
                visible: false, // Hide left price scale by default
            },
            timeScale: {
                borderColor: '#485158',
                timeVisible: true,
                secondsVisible: true,
                fixLeftEdge: false,
                fixRightEdge: false,
                lockVisibleTimeRangeOnResize: false,
                rightOffset: 12,      // Space for live bars to form at 75% mark
                barSpacing: 6,        // Spacing between bars
                minBarSpacing: 0.5,   // Minimum bar spacing for zoom
                visible: true,        // Show timeline on x-axis
                borderVisible: true,
                ticksVisible: true,
                rightBarStaysOnScroll: true, // Keep live bars in view
            },
            // Enhanced scroll and zoom support
            handleScroll: {
                mouseWheel: true,        // Enable mouse wheel zoom
                pressedMouseMove: true,  // Enable pan with mouse drag
                horzTouchDrag: true,     // Enable horizontal touch drag
                vertTouchDrag: true,     // Enable vertical touch drag
            },
            handleScale: {
                mouseWheel: true,        // Enable zoom with mouse wheel
                pinch: true,             // Enable pinch to zoom on touch devices
                axisPressedMouseMove: {
                    time: true,          // Enable time axis scaling (horizontal zoom)
                    price: true,         // Enable price axis scaling (vertical zoom)
                },
                axisDoubleClickReset: {
                    time: true,          // Double-click time axis to reset
                    price: true,         // Double-click price axis to reset
                },
            },
            // Scrollbar support
            scrollbar: {
                horizontal: {
                    visible: true,       // Show horizontal scrollbar
                    size: 16,           // Scrollbar size
                },
                vertical: {
                    visible: true,       // Show vertical scrollbar
                    size: 16,           // Scrollbar size
                },
            },
            width: 800,  // Default width, will be updated in initChart()
            height: 600, // Default height, will be updated in initChart()
        };
        
        // Default view settings
        this.defaultViewSettings = {
            visibleBars: 100,        // Show 100 bars by default
            rightOffset: 25,         // 25% offset for live bars (75% mark)
            autoScale: true,         // Auto-scale price axis
            priceScaleMode: 0,       // Normal price scale mode
        };
    }

    /**
     * Initialize the chart
     */
    initChart() {
        try {
            const container = document.getElementById(this.containerId);
            if (!container) {
                throw new Error(`Container with id '${this.containerId}' not found`);
            }

            // Update chart options with actual container dimensions
            this.chartOptions.width = container.clientWidth || 800;
            this.chartOptions.height = container.clientHeight || 600;

            // Create chart with enhanced options
            this.chart = LightweightCharts.createChart(container, this.chartOptions);
            
            // Apply default view settings
            this.applyDefaultViewSettings();
            
            // Create candlestick series using correct v5.0.8 API
            this.candlestickSeries = this.chart.addSeries(LightweightCharts.CandlestickSeries, {
                upColor: '#4bffb5',
                downColor: '#ff4976',
                borderDownColor: '#ff4976',
                borderUpColor: '#4bffb5',
                wickDownColor: '#ff4976',
                wickUpColor: '#4bffb5',
                priceScaleId: 'right',  // Use right price scale
            });

            // Handle chart resize
            this.setupResizeHandler();
            
            // Setup crosshair move handler for OHLC display
            this.setupCrosshairHandler();
            
            // Setup indicator visibility controls
            this.setupIndicatorControls();

            console.log('✅ Chart initialized successfully with enhanced features');
            return this.chart;
        } catch (error) {
            console.error('❌ Chart initialization failed:', error);
            throw error;
        }
    }

    /**
     * Apply default view settings for optimal chart display
     */
    applyDefaultViewSettings() {
        if (!this.chart) return;
        
        // Set default time scale options
        this.chart.timeScale().applyOptions({
            rightOffset: this.defaultViewSettings.rightOffset,
            barSpacing: 6,
            fixLeftEdge: false,
            fixRightEdge: false,
            lockVisibleTimeRangeOnResize: false,
            rightBarStaysOnScroll: true,
        });
        
        // Set default price scale options
        this.chart.priceScale('right').applyOptions({
            autoScale: this.defaultViewSettings.autoScale,
            mode: this.defaultViewSettings.priceScaleMode,
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        });
        
        console.log('✅ Applied default view settings (live bars at 75% mark)');
    }

    /**
     * Setup indicator visibility controls
     */
    setupIndicatorControls() {
        // Initialize visibility states for all indicators
        this.indicatorVisibility.set('sma_5', true);
        this.indicatorVisibility.set('sma_200', true);
        this.indicatorVisibility.set('fractals_high', true);
        this.indicatorVisibility.set('fractals_low', true);
        this.indicatorVisibility.set('signals', true);
        
        // Setup event listeners for indicator toggle buttons
        const toggleButtons = document.querySelectorAll('.indicator-toggle');
        toggleButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const indicatorId = e.target.closest('.indicator-toggle').dataset.indicator;
                this.toggleIndicatorVisibility(indicatorId);
            });
        });
        
        console.log('✅ Setup indicator visibility controls');
    }

    /**
     * Setup resize handler for responsive chart
     */
    setupResizeHandler() {
        const resizeObserver = new ResizeObserver(entries => {
            if (this.chart && entries.length > 0) {
                const { width, height } = entries[0].contentRect;
                this.chart.applyOptions({ width, height });
            }
        });

        const container = document.getElementById(this.containerId);
        if (container) {
            resizeObserver.observe(container);
        }
    }

    /**
     * Setup crosshair handler for OHLC display
     */
    setupCrosshairHandler() {
        this.chart.subscribeCrosshairMove(param => {
            this.updateOHLCDisplay(param);
        });
    }

    /**
     * Update OHLC display when crosshair moves
     */
    updateOHLCDisplay(param) {
        const ohlcElement = document.getElementById('ohlc-display');
        if (!ohlcElement) return;

        if (param.time) {
            let data = null;
            
            // Try different API approaches for TradingView v5.0.8
            try {
                if (param.seriesPrices && param.seriesPrices.has && param.seriesPrices.has(this.candlestickSeries)) {
                    data = param.seriesPrices.get(this.candlestickSeries);
                } else if (param.seriesData && param.seriesData.has && param.seriesData.has(this.candlestickSeries)) {
                    data = param.seriesData.get(this.candlestickSeries);
                } else {
                    // Fallback: log available properties for debugging
                    console.log('Crosshair param properties:', Object.keys(param));
                    return;
                }
            } catch (error) {
                console.warn('Crosshair data access error:', error);
                return;
            }
            
            if (data) {
                const { open, high, low, close } = data;
                const timestamp = new Date(param.time * 1000).toLocaleString();
                
                ohlcElement.innerHTML = `
                    <div class="ohlc-item">
                        <span class="ohlc-label">Time:</span>
                        <span class="ohlc-value">${timestamp}</span>
                    </div>
                    <div class="ohlc-item">
                        <span class="ohlc-label">O:</span>
                        <span class="ohlc-value">${open.toFixed(2)}</span>
                    </div>
                    <div class="ohlc-item">
                        <span class="ohlc-label">H:</span>
                        <span class="ohlc-value">${high.toFixed(2)}</span>
                    </div>
                    <div class="ohlc-item">
                        <span class="ohlc-label">L:</span>
                        <span class="ohlc-value">${low.toFixed(2)}</span>
                    </div>
                    <div class="ohlc-item">
                        <span class="ohlc-label">C:</span>
                        <span class="ohlc-value ${close >= open ? 'positive' : 'negative'}">${close.toFixed(2)}</span>
                    </div>
                `;
            }
        } else {
            ohlcElement.innerHTML = '<div class="ohlc-item">Hover over chart to see OHLC data</div>';
        }
    }

    /**
     * Load historical data and display on chart with live bars at 75% mark
     */
    async loadHistoricalData(symbol = this.symbol, timeframe = this.currentTimeframe, bars = 500) {
        try {
            console.log(`📊 Loading historical data: ${symbol} ${timeframe} (${bars} bars)`);
            
            const data = await this.dataService.getHistoricalData(symbol, timeframe, bars);
            
            if (data && data.bars && data.bars.length > 0) {
                // Convert data to TradingView format
                const chartData = this.convertToChartFormat(data.bars);
                
                // Set data to candlestick series
                this.candlestickSeries.setData(chartData);
                
                // Apply enhanced view settings for live bars at 75% mark
                this.setupLiveBarsView(chartData);
                
                console.log(`✅ Loaded ${chartData.length} bars for ${symbol} with live bars at 75% mark`);
                return chartData;
            } else {
                console.warn('⚠️ No historical data received');
                return [];
            }
        } catch (error) {
            console.error('❌ Failed to load historical data:', error);
            throw error;
        }
    }

    /**
     * Setup chart view so live bars appear at 75% mark
     */
    setupLiveBarsView(chartData) {
        if (!this.chart || !chartData || chartData.length === 0) return;
        
        // Calculate the time range for optimal view
        const lastBarTime = chartData[chartData.length - 1].time;
        const visibleBars = Math.min(this.defaultViewSettings.visibleBars, chartData.length);
        
        // Set visible range to show the last N bars with live bars at 75% mark
        const firstVisibleBarIndex = Math.max(0, chartData.length - visibleBars);
        const firstVisibleBarTime = chartData[firstVisibleBarIndex].time;
        
        // Apply time scale settings for live bars positioning
        this.chart.timeScale().applyOptions({
            rightOffset: this.defaultViewSettings.rightOffset,
            barSpacing: 6,
            fixLeftEdge: false,
            fixRightEdge: false,
            lockVisibleTimeRangeOnResize: false,
            rightBarStaysOnScroll: true,
        });
        
        // Set the visible range
        this.chart.timeScale().setVisibleRange({
            from: firstVisibleBarTime,
            to: lastBarTime + (lastBarTime - firstVisibleBarTime) * 0.25 // Add 25% space on the right
        });
        
        console.log(`✅ Setup live bars view - visible bars: ${visibleBars}, live bars at 75% mark`);
    }

    /**
     * Convert bars to TradingView chart format
     */
    convertToChartFormat(bars) {
        return bars.map(bar => ({
            // Handle both 'time' (Unix timestamp) and 'timestamp' (ISO string) formats
            time: bar.time || Math.floor(new Date(bar.timestamp).getTime() / 1000),
            open: parseFloat(bar.open),
            high: parseFloat(bar.high),
            low: parseFloat(bar.low),
            close: parseFloat(bar.close),
        }));
    }

    /**
     * Add a new bar to the chart and maintain live bars at 75% mark
     */
    addBar(barData) {
        const chartBar = {
            // Handle both 'time' (Unix timestamp) and 'timestamp' (ISO string) formats
            time: barData.time || Math.floor(new Date(barData.timestamp).getTime() / 1000),
            open: parseFloat(barData.open),
            high: parseFloat(barData.high),
            low: parseFloat(barData.low),
            close: parseFloat(barData.close),
        };

        this.candlestickSeries.update(chartBar);
        
        // Maintain live bars at 75% mark by adjusting the visible range
        this.maintainLiveBarsPosition();
    }

    /**
     * Update the last bar (current bar update) and maintain positioning
     */
    updateLastBar(barData) {
        this.addBar(barData); // Same as addBar for TradingView charts
        
        // Update indicators if they exist
        this.updateIndicatorsForNewBar(barData);
    }

    /**
     * Maintain live bars at 75% mark as new data comes in
     */
    maintainLiveBarsPosition() {
        if (!this.chart) return;
        
        // Get current visible range
        const timeScale = this.chart.timeScale();
        const visibleRange = timeScale.getVisibleRange();
        
        if (visibleRange) {
            // Calculate new range to maintain 75% positioning
            const rangeWidth = visibleRange.to - visibleRange.from;
            const newTo = visibleRange.to + (rangeWidth * 0.1); // Shift slightly
            const newFrom = visibleRange.from + (rangeWidth * 0.1);
            
            // Apply the shift to keep live bars at 75% mark
            timeScale.setVisibleRange({
                from: newFrom,
                to: newTo
            });
        }
    }

    /**
     * Update indicators when new bar data arrives
     */
    updateIndicatorsForNewBar(barData) {
        // This method can be enhanced to update indicators in real-time
        // For now, we'll just log that a new bar was received
        console.log(`📊 Updated bar data - indicators may need refresh`);
    }

    /**
     * Add indicator to chart with enhanced visibility management
     */
    addIndicator(indicatorId, type, config, data) {
        try {
            let series = null;
            const isVisible = this.indicatorVisibility.get(indicatorId) !== false;

            switch (type) {
                case 'sma':
                    series = this.chart.addSeries(LightweightCharts.LineSeries, {
                        color: config.color || '#2196F3',
                        lineWidth: config.lineWidth || 2,
                        title: config.title || `SMA ${config.period}`,
                        visible: isVisible,
                        priceScaleId: 'right',
                        lastValueVisible: true,
                        priceLineVisible: false,
                    });
                    break;

                case 'fractal':
                    // For fractals, we create a line series with special markers
                    series = this.chart.addSeries(LightweightCharts.LineSeries, {
                        color: config.color || '#FF6B6B',
                        lineStyle: config.lineStyle || 1, // Dotted line
                        lineWidth: config.lineWidth || 1,
                        title: config.title || 'Fractals',
                        pointMarkersVisible: false, // We'll use custom markers
                        lastValueVisible: false,
                        priceLineVisible: false,
                        visible: isVisible,
                        priceScaleId: 'right',
                    });
                    
                    // Add the data to the series
                    if (data && data.length > 0) {
                        series.setData(data);
                        
                        // Create markers for fractal points
                        const fractalMarkers = data.map(point => ({
                            time: point.time,
                            position: config.fractalsType === 'high' ? 'aboveBar' : 'belowBar',
                            color: config.color,
                            shape: config.fractalsType === 'high' ? 'circle' : 'circle',
                            text: config.fractalsType === 'high' ? '▲' : '▼',
                            size: 1
                        }));
                        
                        // Add markers to candlestick series if available
                        if (this.candlestickSeries) {
                            // Use the new marker management system
                            this.addMarkers(indicatorId, fractalMarkers);
                        }
                    }
                    break;

                case 'signal':
                    // Signals will be markers, not a separate series
                    this.addSignalMarkers(data);
                    return;

                default:
                    console.warn(`⚠️ Unknown indicator type: ${type}`);
                    return;
            }

            if (series && data) {
                series.setData(data);
                this.indicators.set(indicatorId, {
                    series,
                    type,
                    config,
                    visible: isVisible
                });
                
                // Update visibility state
                this.indicatorVisibility.set(indicatorId, isVisible);
            }

            console.log(`✅ Added indicator: ${indicatorId} (${type}) - Visible: ${isVisible}`);
        } catch (error) {
            console.error(`❌ Failed to add indicator ${indicatorId}:`, error);
        }
    }

    /**
     * Add signal markers to chart
     */
    addSignalMarkers(signals) {
        if (!this.candlestickSeries || !signals || signals.length === 0) return;

        const markers = signals.map(signal => ({
            time: Math.floor(new Date(signal.timestamp).getTime() / 1000),
            position: signal.direction === 'LONG' ? 'belowBar' : 'aboveBar',
            color: signal.direction === 'LONG' ? '#4bffb5' : '#ff4976',
            shape: signal.direction === 'LONG' ? 'arrowUp' : 'arrowDown',
            text: `${signal.direction} @ ${signal.entry_price}`,
        }));

        // Use the new marker management system
        this.addMarkers('signals', markers);
    }

    /**
     * Enhanced method to toggle indicator visibility with UI updates
     */
    toggleIndicatorVisibility(indicatorId) {
        const currentVisibility = this.indicatorVisibility.get(indicatorId) !== false;
        const newVisibility = !currentVisibility;
        
        // Update visibility state
        this.indicatorVisibility.set(indicatorId, newVisibility);
        
        // Handle different indicator types
        if (indicatorId === 'signals') {
            // Toggle signal markers visibility
            this.toggleSignalMarkersVisibility(newVisibility);
        } else if (indicatorId.startsWith('fractals_')) {
            // Toggle fractal markers visibility
            this.toggleFractalMarkersVisibility(indicatorId, newVisibility);
        } else {
            // Toggle regular indicator series
            const indicator = this.indicators.get(indicatorId);
            if (indicator && indicator.series) {
                indicator.visible = newVisibility;
                indicator.series.applyOptions({
                    visible: newVisibility
                });
            }
        }
        
        // Update UI button state
        this.updateIndicatorToggleButton(indicatorId, newVisibility);
        
        console.log(`${newVisibility ? '👁️' : '🙈'} Toggled ${indicatorId} visibility: ${newVisibility}`);
        return newVisibility;
    }

    /**
     * Update indicator toggle button appearance
     */
    updateIndicatorToggleButton(indicatorId, isVisible) {
        const button = document.querySelector(`[data-indicator="${indicatorId}"]`);
        if (button) {
            const icon = button.querySelector('.toggle-icon');
            if (icon) {
                icon.textContent = isVisible ? '👁️' : '🙈';
            }
            button.classList.toggle('indicator-hidden', !isVisible);
            button.title = isVisible ? 'Hide' : 'Show';
        }
    }

    /**
     * Toggle signal markers visibility
     */
    toggleSignalMarkersVisibility(isVisible) {
        // For now, we'll need to re-add or remove signal markers
        // This is a limitation of the current TradingView API
        if (isVisible) {
            // Re-add signal markers if we have them stored
            const signalMarkers = this.markers.get('signals');
            if (signalMarkers) {
                this.candlestickSeries.setMarkers(this.getAllVisibleMarkers());
            }
        } else {
            // Remove signal markers by filtering them out
            const allMarkers = this.getAllVisibleMarkers();
            const filteredMarkers = allMarkers.filter(marker => 
                !marker.text || !marker.text.includes('@')
            );
            this.candlestickSeries.setMarkers(filteredMarkers);
        }
    }

    /**
     * Toggle fractal markers visibility
     */
    toggleFractalMarkersVisibility(indicatorId, isVisible) {
        // Similar to signals, we need to manage fractal markers
        const fractalType = indicatorId.replace('fractals_', '');
        
        if (isVisible) {
            // Re-add fractal markers
            const allMarkers = this.getAllVisibleMarkers();
            this.candlestickSeries.setMarkers(allMarkers);
        } else {
            // Remove fractal markers of this type
            const allMarkers = this.getAllVisibleMarkers();
            const filteredMarkers = allMarkers.filter(marker => {
                if (fractalType === 'high') {
                    return marker.text !== '▲';
                } else if (fractalType === 'low') {
                    return marker.text !== '▼';
                }
                return true;
            });
            this.candlestickSeries.setMarkers(filteredMarkers);
        }
    }

    /**
     * Get all visible markers based on current visibility settings
     */
    getAllVisibleMarkers() {
        const allMarkers = [];
        
        this.markers.forEach((markerSet, markerId) => {
            let shouldInclude = true;
            
            // Check visibility based on marker type
            if (markerId === 'signals') {
                shouldInclude = this.indicatorVisibility.get('signals') !== false;
            } else if (markerId.includes('fractals')) {
                const fractalType = markerId.includes('high') ? 'fractals_high' : 'fractals_low';
                shouldInclude = this.indicatorVisibility.get(fractalType) !== false;
            }
            
            if (shouldInclude) {
                allMarkers.push(...markerSet);
            }
        });
        
        return allMarkers;
    }

    /**
     * Remove indicator from chart
     */
    removeIndicator(indicatorId) {
        const indicator = this.indicators.get(indicatorId);
        if (!indicator) return;

        this.chart.removeSeries(indicator.series);
        this.indicators.delete(indicatorId);
        
        // Also remove associated markers
        this.removeMarkers(indicatorId);
        
        console.log(`🗑️ Removed indicator: ${indicatorId}`);
    }

    /**
     * Update timeframe
     */
    async updateTimeframe(timeframe) {
        if (timeframe === this.currentTimeframe) return;

        console.log(`📅 Changing timeframe from ${this.currentTimeframe} to ${timeframe}`);
        
        this.currentTimeframe = timeframe;
        
        // Reload data with new timeframe
        await this.loadHistoricalData(this.symbol, timeframe);
        
        // Reload indicators if any
        await this.reloadIndicators();
    }

    /**
     * Reload indicators after timeframe change
     */
    async reloadIndicators() {
        try {
            console.log(`🔄 Reloading indicators for timeframe: ${this.currentTimeframe}`);
            
            const indicatorData = await this.dataService.getIndicatorData('sma_fractal_scalper', this.currentTimeframe);
            
            // Clear existing indicators completely
            this.clearAllIndicators();

            // Re-add indicators with new data
            if (indicatorData.sma_5) {
                this.addIndicator('sma_5', 'sma', {
                    color: '#2196F3',
                    title: '5-SMA (Fast)',
                    period: 5
                }, indicatorData.sma_5);
            }

            if (indicatorData.sma_200) {
                this.addIndicator('sma_200', 'sma', {
                    color: '#FF9800',
                    title: '200-SMA (Slow)',
                    period: 200
                }, indicatorData.sma_200);
            }

            if (indicatorData.fractals) {
                // Process fractals separately for high and low
                const highFractals = indicatorData.fractals.filter(f => f.type === 'high');
                const lowFractals = indicatorData.fractals.filter(f => f.type === 'low');
                
                if (highFractals.length > 0) {
                    this.addMarkersAsLineSeries('high_fractals', highFractals.map(f => ({
                        time: Math.floor(new Date(f.timestamp).getTime() / 1000),
                        value: f.price
                    })));
                }
                
                if (lowFractals.length > 0) {
                    this.addMarkersAsLineSeries('low_fractals', lowFractals.map(f => ({
                        time: Math.floor(new Date(f.timestamp).getTime() / 1000),
                        value: f.price
                    })));
                }
            }

            if (indicatorData.signals) {
                this.addSignalMarkers(indicatorData.signals);
            }

            console.log(`✅ Reloaded indicators for timeframe: ${this.currentTimeframe}`);

        } catch (error) {
            console.error('❌ Failed to reload indicators:', error);
        }
    }

    /**
     * Clear all indicators and markers
     */
    clearAllIndicators() {
        // Remove all indicators
        this.indicators.forEach((indicator, id) => {
            this.chart.removeSeries(indicator.series);
        });
        this.indicators.clear();
        
        // Remove all marker series
        if (this.markerSeries) {
            this.markerSeries.forEach((series, id) => {
                this.chart.removeSeries(series);
            });
            this.markerSeries.clear();
        }
        
        // Clear marker storage
        this.markers.clear();
        
        console.log('🧹 Cleared all indicators and markers');
    }

    /**
     * Zoom to specific time range
     */
    zoomToRange(from, to) {
        if (this.chart) {
            this.chart.timeScale().setVisibleRange({ from, to });
        }
    }

    /**
     * Fit chart content
     */
    fitContent() {
        if (this.chart) {
            this.chart.timeScale().fitContent();
        }
    }

    /**
     * Get chart screenshot
     */
    takeScreenshot() {
        if (this.chart) {
            return this.chart.takeScreenshot();
        }
        return null;
    }

    /**
     * Destroy chart and cleanup
     */
    destroy() {
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
            this.candlestickSeries = null;
            this.indicators.clear();
        }
    }

    /**
     * Add markers to chart with proper management
     */
    addMarkers(markerId, markers) {
        if (!this.candlestickSeries || !markers || markers.length === 0) {
            console.warn(`⚠️ Cannot add markers for ${markerId}: candlestick series not initialized or no markers provided`);
            return;
        }

        // Store markers by ID
        this.markers.set(markerId, markers);
        
        // Combine all markers and set them on the candlestick series
        const allMarkers = [];
        this.markers.forEach(markerSet => {
            allMarkers.push(...markerSet);
        });
        
        try {
            // For now, skip the createSeriesMarkers approach due to internal library errors
            // and go directly to the line series approach which should work reliably
            console.log(`🔄 Using line series approach for ${markerId} (skipping createSeriesMarkers due to library issues)`);
            this.addMarkersAsLineSeries(markerId, markers);
            
            /* Commented out until library issues are resolved
            // In TradingView v5.0.8, check if createSeriesMarkers exists
            if (typeof LightweightCharts.createSeriesMarkers === 'function') {
                // Use the new v5.0.8 API
                console.log(`🔄 Using createSeriesMarkers API for ${markerId}`);
                this.candlestickSeries.seriesMarkers = LightweightCharts.createSeriesMarkers(this.chart, this.candlestickSeries, {
                    markers: allMarkers
                });
                console.log(`✅ Added ${markers.length} markers for ${markerId} using createSeriesMarkers`);
            } else if (typeof this.candlestickSeries.setMarkers === 'function') {
                // Fallback to older API
                console.log(`🔄 Using legacy setMarkers API for ${markerId}`);
                this.candlestickSeries.setMarkers(allMarkers);
                console.log(`✅ Added ${markers.length} markers for ${markerId} using setMarkers`);
            } else {
                // Alternative approach: Use line series with custom markers
                console.log(`🔄 Using alternative approach with line series for ${markerId}`);
                this.addMarkersAsLineSeries(markerId, markers);
            }
            */
        } catch (error) {
            console.error(`❌ Failed to set markers for ${markerId}:`, error);
            console.log('Trying alternative approach...');
            this.addMarkersAsLineSeries(markerId, markers);
        }
    }

    /**
     * Alternative approach: Add markers as line series with point markers
     */
    addMarkersAsLineSeries(markerId, markers) {
        try {
            // For fractal markers, we want to show them as individual points
            // Create a line series for the markers
            const markerColor = markerId.includes('high') ? '#E91E63' : 
                               markerId.includes('low') ? '#4CAF50' : '#FF6B6B';
            
            const markerSeries = this.chart.addSeries(LightweightCharts.LineSeries, {
                color: markerColor,
                lineWidth: 0, // No connecting lines
                pointMarkersVisible: true,
                pointMarkersRadius: 4,
                lastValueVisible: false,
                priceLineVisible: false,
                title: `${markerId} Markers`,
            });

            // Convert markers to line series data
            // Handle both marker format and fractal data format
            const lineData = markers.map(marker => {
                // Support both marker format and direct fractal data format
                const time = marker.time || Math.floor(new Date(marker.timestamp).getTime() / 1000);
                const value = marker.value || marker.price;
                
                return {
                    time: time,
                    value: value
                };
            }).filter(point => point.time && point.value); // Filter out invalid points

            if (lineData.length > 0) {
                markerSeries.setData(lineData);
                
                // Store the marker series for cleanup
                if (!this.markerSeries) {
                    this.markerSeries = new Map();
                }
                this.markerSeries.set(markerId, markerSeries);
                
                console.log(`✅ Added ${lineData.length} markers for ${markerId} using line series approach`);
            } else {
                console.warn(`⚠️ No valid marker data for ${markerId}`);
                // Remove the empty series
                this.chart.removeSeries(markerSeries);
            }
        } catch (error) {
            console.error(`❌ Failed to add markers as line series for ${markerId}:`, error);
        }
    }

    /**
     * Remove markers by ID
     */
    removeMarkers(markerId) {
        if (!this.markers.has(markerId)) return;
        
        this.markers.delete(markerId);
        
        // Also remove marker series if it exists
        if (this.markerSeries && this.markerSeries.has(markerId)) {
            const markerSeries = this.markerSeries.get(markerId);
            this.chart.removeSeries(markerSeries);
            this.markerSeries.delete(markerId);
            console.log(`🗑️ Removed marker series for ${markerId}`);
        }
        
        // Update remaining markers on candlestick series
        const allMarkers = [];
        this.markers.forEach(markerSet => {
            allMarkers.push(...markerSet);
        });
        
        try {
            if (typeof this.candlestickSeries.setMarkers === 'function') {
                this.candlestickSeries.setMarkers(allMarkers);
            }
        } catch (error) {
            console.warn(`Warning: Could not update markers after removal:`, error);
        }
        
        console.log(`🗑️ Removed markers for ${markerId}`);
    }
}

export default ChartManager; 