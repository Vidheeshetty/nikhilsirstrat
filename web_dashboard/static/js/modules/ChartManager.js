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
        this.currentTimeframe = '1m';
        this.symbol = 'GOLDGUINEA';
        
        // Chart configuration
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
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#485158',
            },
            timeScale: {
                borderColor: '#485158',
                timeVisible: true,
                secondsVisible: false,
            },
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

            // Create chart
            this.chart = LightweightCharts.createChart(container, this.chartOptions);
            
            // Create candlestick series
            this.candlestickSeries = this.chart.addCandlestickSeries({
                upColor: '#4bffb5',
                downColor: '#ff4976',
                borderDownColor: '#ff4976',
                borderUpColor: '#4bffb5',
                wickDownColor: '#ff4976',
                wickUpColor: '#4bffb5',
            });

            // Handle chart resize
            this.setupResizeHandler();
            
            // Setup crosshair move handler for OHLC display
            this.setupCrosshairHandler();

            console.log('✅ Chart initialized successfully');
            return this.chart;
        } catch (error) {
            console.error('❌ Chart initialization failed:', error);
            throw error;
        }
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
            const data = param.seriesPrices.get(this.candlestickSeries);
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
     * Load historical data and display on chart
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
                
                // Fit chart to content
                this.chart.timeScale().fitContent();
                
                console.log(`✅ Loaded ${chartData.length} bars for ${symbol}`);
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
     * Convert bar data to TradingView Lightweight Charts format
     */
    convertToChartFormat(bars) {
        return bars.map(bar => ({
            time: Math.floor(new Date(bar.timestamp).getTime() / 1000),
            open: parseFloat(bar.open),
            high: parseFloat(bar.high),
            low: parseFloat(bar.low),
            close: parseFloat(bar.close),
        }));
    }

    /**
     * Add a new bar (real-time update)
     */
    addBar(barData) {
        if (!this.candlestickSeries) return;

        const chartBar = {
            time: Math.floor(new Date(barData.timestamp).getTime() / 1000),
            open: parseFloat(barData.open),
            high: parseFloat(barData.high),
            low: parseFloat(barData.low),
            close: parseFloat(barData.close),
        };

        this.candlestickSeries.update(chartBar);
    }

    /**
     * Update the last bar (current bar update)
     */
    updateLastBar(barData) {
        this.addBar(barData); // Same as addBar for TradingView charts
    }

    /**
     * Add indicator to chart
     */
    addIndicator(indicatorId, type, config, data) {
        try {
            let series = null;

            switch (type) {
                case 'sma':
                    series = this.chart.addLineSeries({
                        color: config.color || '#2196F3',
                        lineWidth: config.lineWidth || 2,
                        title: config.title || `SMA ${config.period}`,
                    });
                    break;

                case 'fractal':
                    series = this.chart.addLineSeries({
                        color: config.color || '#FF6B6B',
                        lineStyle: LightweightCharts.LineStyle.Dotted,
                        lineWidth: 1,
                        title: config.title || 'Fractals',
                        pointMarkersVisible: true,
                    });
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
                    visible: true
                });
            }

            console.log(`✅ Added indicator: ${indicatorId} (${type})`);
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

        this.candlestickSeries.setMarkers(markers);
        console.log(`✅ Added ${markers.length} signal markers`);
    }

    /**
     * Toggle indicator visibility
     */
    toggleIndicator(indicatorId) {
        const indicator = this.indicators.get(indicatorId);
        if (!indicator) return;

        indicator.visible = !indicator.visible;
        indicator.series.applyOptions({
            visible: indicator.visible
        });

        console.log(`${indicator.visible ? '👁️' : '🙈'} Toggled ${indicatorId} visibility`);
        return indicator.visible;
    }

    /**
     * Remove indicator from chart
     */
    removeIndicator(indicatorId) {
        const indicator = this.indicators.get(indicatorId);
        if (!indicator) return;

        this.chart.removeSeries(indicator.series);
        this.indicators.delete(indicatorId);
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
            const indicatorData = await this.dataService.getIndicatorData('sma_fractal_scalper', this.currentTimeframe);
            
            // Clear existing indicators
            this.indicators.forEach((indicator, id) => {
                this.removeIndicator(id);
            });

            // Re-add indicators with new data
            if (indicatorData.sma_5) {
                this.addIndicator('sma_5', 'sma', {
                    color: '#2196F3',
                    title: '5-SMA',
                    period: 5
                }, indicatorData.sma_5);
            }

            if (indicatorData.sma_200) {
                this.addIndicator('sma_200', 'sma', {
                    color: '#FF9800',
                    title: '200-SMA',
                    period: 200
                }, indicatorData.sma_200);
            }

            if (indicatorData.fractals) {
                this.addIndicator('fractals', 'fractal', {
                    color: '#E91E63',
                    title: 'Fractals'
                }, indicatorData.fractals);
            }

            if (indicatorData.signals) {
                this.addSignalMarkers(indicatorData.signals);
            }

        } catch (error) {
            console.error('❌ Failed to reload indicators:', error);
        }
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
}

export default ChartManager; 