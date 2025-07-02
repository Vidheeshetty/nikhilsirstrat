/**
 * DataService - Handles all data communication with backend
 * Uses WebSocket for real-time updates, REST API for initial data
 */
class DataService {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.websocket = null;
        this.eventHandlers = new Map();
        this.cache = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    /**
     * Initialize WebSocket connection for real-time updates
     */
    async connectWebSocket() {
        try {
            const wsUrl = this.baseUrl.replace('http', 'ws') + '/ws/chart';
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected');
                this.reconnectAttempts = 0;
                this.emit('connection', { status: 'connected' });
            };

            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('❌ WebSocket message parse error:', error);
                }
            };

            this.websocket.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.emit('connection', { status: 'disconnected' });
                this.handleReconnect();
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.emit('connection', { status: 'error', error });
            };

        } catch (error) {
            console.error('❌ WebSocket connection failed:', error);
            this.handleReconnect();
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleWebSocketMessage(message) {
        const { type, data, timestamp } = message;
        
        // Emit event to registered handlers
        this.emit(type, { data, timestamp });
        
        // Update cache if needed
        if (type === 'bar_update') {
            this.updateBarCache(data);
        }
    }

    /**
     * Handle WebSocket reconnection
     */
    handleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }

    /**
     * Subscribe to WebSocket events
     */
    subscribe(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        this.eventHandlers.get(eventType).push(handler);
    }

    /**
     * Unsubscribe from WebSocket events
     */
    unsubscribe(eventType, handler) {
        if (this.eventHandlers.has(eventType)) {
            const handlers = this.eventHandlers.get(eventType);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    /**
     * Emit event to all registered handlers
     */
    emit(eventType, data) {
        if (this.eventHandlers.has(eventType)) {
            this.eventHandlers.get(eventType).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`❌ Event handler error for ${eventType}:`, error);
                }
            });
        }
    }

    /**
     * Get historical chart data
     */
    async getHistoricalData(symbol = 'GOLDGUINEA', timeframe = '1m', bars = 500) {
        try {
            const response = await fetch(
                `${this.baseUrl}/api/chart/data?symbol=${symbol}&timeframe=${timeframe}&bars=${bars}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Cache the data
            const cacheKey = `${symbol}_${timeframe}_${bars}`;
            this.cache.set(cacheKey, data);
            
            return data;
        } catch (error) {
            console.error('❌ Failed to fetch historical data:', error);
            throw error;
        }
    }

    /**
     * Get indicator data for strategy
     */
    async getIndicatorData(strategy = 'sma_fractal_scalper', timeframe = '1m') {
        try {
            const response = await fetch(
                `${this.baseUrl}/api/chart/indicators?strategy=${strategy}&timeframe=${timeframe}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('❌ Failed to fetch indicator data:', error);
            throw error;
        }
    }

    /**
     * Update bar cache with new data
     */
    updateBarCache(data) {
        const { symbol, timeframe, bar } = data;
        const cacheKey = `${symbol}_${timeframe}_bars`;
        
        if (this.cache.has(cacheKey)) {
            const cachedData = this.cache.get(cacheKey);
            if (cachedData.bars) {
                // Add new bar or update last bar
                const lastBar = cachedData.bars[cachedData.bars.length - 1];
                if (lastBar && lastBar.timestamp === bar.timestamp) {
                    // Update existing bar
                    cachedData.bars[cachedData.bars.length - 1] = bar;
                } else {
                    // Add new bar
                    cachedData.bars.push(bar);
                    
                    // Keep only last 1000 bars in cache
                    if (cachedData.bars.length > 1000) {
                        cachedData.bars = cachedData.bars.slice(-1000);
                    }
                }
            }
        }
    }

    /**
     * Get cached data
     */
    getCachedData(symbol, timeframe, bars) {
        const cacheKey = `${symbol}_${timeframe}_${bars}`;
        return this.cache.get(cacheKey);
    }

    /**
     * Send message via WebSocket
     */
    send(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        } else {
            console.warn('⚠️ WebSocket not connected, cannot send message');
        }
    }

    /**
     * Close WebSocket connection
     */
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
}

export default DataService; 