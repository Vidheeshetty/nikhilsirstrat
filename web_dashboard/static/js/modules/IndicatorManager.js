/**
 * IndicatorManager - Manages strategy indicators and their display
 * Handles SMA, Fractals, and Signal indicators for the SMA Fractal Scalper strategy
 */
class IndicatorManager {
    constructor(chartManager, dataService) {
        this.chartManager = chartManager;
        this.dataService = dataService;
        this.indicators = new Map();
        this.strategy = 'sma_fractal_scalper';
        this.updateInterval = null;
    }

    /**
     * Initialize indicators for the current strategy
     */
    async initializeIndicators(timeframe = '1m') {
        try {
            console.log(`🔧 Initializing indicators for ${this.strategy} (${timeframe})`);
            
            // Get indicator data from backend
            const indicatorData = await this.dataService.getIndicatorData(this.strategy, timeframe);
            
            if (!indicatorData) {
                console.warn('⚠️ No indicator data received');
                return;
            }

            // Add SMA indicators
            await this.addSMAIndicators(indicatorData);
            
            // Add Fractal indicators
            await this.addFractalIndicators(indicatorData);
            
            // Add Signal markers
            await this.addSignalMarkers(indicatorData);
            
            console.log('✅ Indicators initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize indicators:', error);
        }
    }

    /**
     * Add SMA indicators to chart
     */
    async addSMAIndicators(indicatorData) {
        // 5-period SMA (Fast)
        if (indicatorData.sma_5 && indicatorData.sma_5.length > 0) {
            const sma5Data = this.convertIndicatorData(indicatorData.sma_5);
            this.chartManager.addIndicator('sma_5', 'sma', {
                color: '#2196F3',
                lineWidth: 2,
                title: '5-SMA (Fast)',
                period: 5
            }, sma5Data);
            
            this.indicators.set('sma_5', {
                type: 'sma',
                period: 5,
                color: '#2196F3',
                visible: true,
                data: sma5Data
            });
        }

        // 200-period SMA (Slow)
        if (indicatorData.sma_200 && indicatorData.sma_200.length > 0) {
            const sma200Data = this.convertIndicatorData(indicatorData.sma_200);
            this.chartManager.addIndicator('sma_200', 'sma', {
                color: '#FF9800',
                lineWidth: 2,
                title: '200-SMA (Slow)',
                period: 200
            }, sma200Data);
            
            this.indicators.set('sma_200', {
                type: 'sma',
                period: 200,
                color: '#FF9800',
                visible: true,
                data: sma200Data
            });
        }
    }

    /**
     * Add Fractal indicators to chart
     */
    async addFractalIndicators(indicatorData) {
        if (indicatorData.fractals && indicatorData.fractals.length > 0) {
            // Separate high and low fractals
            const highFractals = indicatorData.fractals
                .filter(fractal => fractal.type === 'high')
                .map(fractal => ({
                    time: fractal.time || Math.floor(new Date(fractal.timestamp).getTime() / 1000),
                    value: fractal.price
                }));

            const lowFractals = indicatorData.fractals
                .filter(fractal => fractal.type === 'low')
                .map(fractal => ({
                    time: fractal.time || Math.floor(new Date(fractal.timestamp).getTime() / 1000),
                    value: fractal.price
                }));

            // Add high fractals as line series with markers
            if (highFractals.length > 0) {
                this.chartManager.addIndicator('fractals_high', 'fractal', {
                    color: '#E91E63',
                    lineWidth: 1,
                    lineStyle: 1, // Dotted line
                    title: 'High Fractals (5-bar)',
                    fractalsType: 'high'
                }, highFractals);
                
                this.indicators.set('fractals_high', {
                    type: 'fractal',
                    color: '#E91E63',
                    visible: true,
                    data: highFractals,
                    window: 5  // From strategy config
                });
            }

            // Add low fractals as line series with markers
            if (lowFractals.length > 0) {
                this.chartManager.addIndicator('fractals_low', 'fractal', {
                    color: '#4CAF50',
                    lineWidth: 1,
                    lineStyle: 1, // Dotted line
                    title: 'Low Fractals (5-bar)',
                    fractalsType: 'low'
                }, lowFractals);
                
                this.indicators.set('fractals_low', {
                    type: 'fractal',
                    color: '#4CAF50',
                    visible: true,
                    data: lowFractals,
                    window: 5  // From strategy config
                });
            }
        } else {
            console.log('ℹ️ No fractal data available - indicators will show when fractals are detected');
            
            // Create placeholder indicators for UI consistency
            this.indicators.set('fractals_high', {
                type: 'fractal',
                color: '#E91E63',
                visible: true,
                data: [],
                window: 5
            });
            
            this.indicators.set('fractals_low', {
                type: 'fractal',
                color: '#4CAF50',
                visible: true,
                data: [],
                window: 5
            });
        }
    }

    /**
     * Add Signal markers to chart
     */
    async addSignalMarkers(indicatorData) {
        if (indicatorData.signals && indicatorData.signals.length > 0) {
            this.chartManager.addSignalMarkers(indicatorData.signals);
            
            this.indicators.set('signals', {
                type: 'signal',
                visible: true,
                data: indicatorData.signals
            });
        }
    }

    /**
     * Convert indicator data to chart format
     */
    convertIndicatorData(data) {
        return data.map(point => ({
            // Handle both 'time' (Unix) and 'timestamp' (ISO) formats
            time: point.time || Math.floor(new Date(point.timestamp).getTime() / 1000),
            value: parseFloat(point.value)
        }));
    }

    /**
     * Get indicator configuration for UI
     */
    getIndicatorConfig() {
        const config = [];
        
        this.indicators.forEach((indicator, id) => {
            config.push({
                id,
                type: indicator.type,
                color: indicator.color,
                visible: indicator.visible,
                title: this.getIndicatorTitle(id, indicator)
            });
        });
        
        return config;
    }

    /**
     * Get human-readable indicator title
     */
    getIndicatorTitle(id, indicator) {
        switch (id) {
            case 'sma_5':
                return '5-Period SMA (Fast)';
            case 'sma_200':
                return '200-Period SMA (Slow)';
            case 'fractals_high':
                return 'High Fractals';
            case 'fractals_low':
                return 'Low Fractals';
            case 'signals':
                return 'Trade Signals';
            default:
                return id.replace('_', ' ').toUpperCase();
        }
    }

    /**
     * Toggle indicator visibility
     */
    toggleIndicator(indicatorId) {
        const indicator = this.indicators.get(indicatorId);
        if (!indicator) {
            console.warn(`⚠️ Indicator ${indicatorId} not found`);
            return false;
        }
        
        indicator.visible = !indicator.visible;
        
        // Toggle in chart manager
        this.chartManager.toggleIndicator(indicatorId);
        
        console.log(`${indicator.visible ? '👁️' : '🙈'} Toggled ${indicatorId} visibility`);
        return indicator.visible;
    }

    /**
     * Get current indicator values for display
     */
    getCurrentValues() {
        const values = {};
        
        this.indicators.forEach((indicator, id) => {
            if (indicator.data && indicator.data.length > 0) {
                const lastValue = indicator.data[indicator.data.length - 1];
                values[id] = {
                    value: lastValue.value,
                    timestamp: lastValue.time,
                    type: indicator.type
                };
            }
        });
        
        return values;
    }

    /**
     * Get trend status based on SMA crossover
     */
    getTrendStatus() {
        const sma5 = this.indicators.get('sma_5');
        const sma200 = this.indicators.get('sma_200');
        
        if (!sma5 || !sma200 || !sma5.data || !sma200.data) {
            return { trend: 'UNKNOWN', confidence: 0 };
        }
        
        const sma5Value = sma5.data[sma5.data.length - 1]?.value;
        const sma200Value = sma200.data[sma200.data.length - 1]?.value;
        
        if (sma5Value && sma200Value) {
            const trend = sma5Value > sma200Value ? 'BULLISH' : 'BEARISH';
            const spread = Math.abs(sma5Value - sma200Value);
            const confidence = Math.min(spread / sma200Value * 100, 100);
            
            return { trend, confidence: confidence.toFixed(2) };
        }
        
        return { trend: 'UNKNOWN', confidence: 0 };
    }

    /**
     * Handle indicator updates
     */
    handleIndicatorUpdate(updateData) {
        const { type, data, timestamp } = updateData;
        
        switch (type) {
            case 'sma_update':
                this.updateSMAIndicators(data, timestamp);
                break;
                
            case 'fractal_update':
                this.updateFractalIndicators(data, timestamp);
                break;
                
            case 'signal_generated':
                this.addNewSignal(data, timestamp);
                break;
                
            default:
                console.warn(`⚠️ Unknown indicator update type: ${type}`);
        }
    }

    /**
     * Update SMA indicators with new data
     */
    updateSMAIndicators(data, timestamp) {
        const time = Math.floor(new Date(timestamp).getTime() / 1000);
        
        // Update 5-SMA
        if (data.sma_5 !== undefined) {
            const indicator = this.indicators.get('sma_5');
            if (indicator && indicator.data) {
                const newPoint = { time, value: parseFloat(data.sma_5) };
                
                // Update last point or add new point
                const lastPoint = indicator.data[indicator.data.length - 1];
                if (lastPoint && lastPoint.time === time) {
                    indicator.data[indicator.data.length - 1] = newPoint;
                } else {
                    indicator.data.push(newPoint);
                }
                
                // Update chart
                const chartIndicator = this.chartManager.indicators.get('sma_5');
                if (chartIndicator) {
                    chartIndicator.series.update(newPoint);
                }
            }
        }
        
        // Update 200-SMA
        if (data.sma_200 !== undefined) {
            const indicator = this.indicators.get('sma_200');
            if (indicator && indicator.data) {
                const newPoint = { time, value: parseFloat(data.sma_200) };
                
                // Update last point or add new point
                const lastPoint = indicator.data[indicator.data.length - 1];
                if (lastPoint && lastPoint.time === time) {
                    indicator.data[indicator.data.length - 1] = newPoint;
                } else {
                    indicator.data.push(newPoint);
                }
                
                // Update chart
                const chartIndicator = this.chartManager.indicators.get('sma_200');
                if (chartIndicator) {
                    chartIndicator.series.update(newPoint);
                }
            }
        }
    }

    /**
     * Update Fractal indicators with new data
     */
    updateFractalIndicators(data, timestamp) {
        if (!data.fractals) return;
        
        const time = Math.floor(new Date(timestamp).getTime() / 1000);
        
        data.fractals.forEach(fractal => {
            const indicatorId = `fractals_${fractal.type}`;
            const indicator = this.indicators.get(indicatorId);
            
            if (indicator && indicator.data) {
                const newPoint = { time, value: parseFloat(fractal.price) };
                indicator.data.push(newPoint);
                
                // Update chart
                const chartIndicator = this.chartManager.indicators.get(indicatorId);
                if (chartIndicator) {
                    chartIndicator.series.update(newPoint);
                }
            }
        });
    }

    /**
     * Add new signal marker
     */
    addNewSignal(signalData, timestamp) {
        const indicator = this.indicators.get('signals');
        if (indicator && indicator.data) {
            const newSignal = {
                ...signalData,
                timestamp
            };
            
            indicator.data.push(newSignal);
            
            // Update chart markers
            this.chartManager.addSignalMarkers([newSignal]);
        }
    }

    /**
     * Start real-time indicator updates
     */
    startRealTimeUpdates() {
        // Subscribe to indicator update events
        this.dataService.subscribe('indicator_update', (data) => {
            this.handleIndicatorUpdate(data);
        });
        
        this.dataService.subscribe('signal_generated', (data) => {
            this.handleIndicatorUpdate({
                type: 'signal_generated',
                data: data.data,
                timestamp: data.timestamp
            });
        });
        
        console.log('🔄 Started real-time indicator updates');
    }

    /**
     * Stop real-time indicator updates
     */
    stopRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        console.log('⏹️ Stopped real-time indicator updates');
    }

    /**
     * Clear all indicators
     */
    clearIndicators() {
        this.indicators.forEach((indicator, id) => {
            this.chartManager.removeIndicator(id);
        });
        
        this.indicators.clear();
        console.log('🧹 Cleared all indicators');
    }

    /**
     * Reload indicators for new timeframe
     */
    async reloadIndicators(timeframe) {
        this.clearIndicators();
        await this.initializeIndicators(timeframe);
    }
}

export default IndicatorManager; 