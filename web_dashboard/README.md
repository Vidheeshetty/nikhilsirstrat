# Trading Dashboard

A professional real-time trading dashboard for monitoring the SMA Fractal Scalper strategy.

## 🚀 Features

### Interactive Charting
- **TradingView Lightweight Charts** integration
- Real-time OHLC candlestick display
- Multiple timeframe support (1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d)
- Horizontal scrolling and zoom functionality
- Crosshair with OHLC data display

### Strategy Indicators
- **5-SMA (Fast)** - Blue line indicator
- **200-SMA (Slow)** - Orange line indicator  
- **Fractal Markers** - High/Low fractal points
- **Trade Signals** - Entry/Exit arrows on chart
- Toggle visibility for each indicator

### Real-Time Updates
- **WebSocket-based** push notifications
- Live price updates every 10 seconds
- Real-time indicator calculations
- Signal generation alerts
- Trade execution notifications

### Trading Metrics
- Current price and SMA trend status
- Total signals and executed trades
- Strategy performance metrics
- Real-time activity feed
- Connection status monitoring

## 🏗️ Architecture

```
web_dashboard/
├── static/
│   ├── css/
│   │   └── dashboard.css          # Styling
│   ├── js/
│   │   ├── modules/
│   │   │   ├── DataService.js     # WebSocket & API
│   │   │   ├── ChartManager.js    # Chart handling
│   │   │   ├── IndicatorManager.js # Strategy indicators
│   │   │   └── TimeframeManager.js # Multi-timeframe
│   │   └── dashboard.js           # Main application
│   └── libs/
│       └── lightweight-charts.standalone.production.js
└── templates/
    └── chart.html                 # Main dashboard HTML
```

## 🔧 Setup

### Prerequisites
- Paper trading daemon running
- FastAPI server with chart endpoints
- Modern web browser with ES6 module support

### Access
1. Start the paper trading server:
   ```bash
   python3 scripts/paper_trading/paper_trading_server.py \
     --config config/paper_trading/my_zerodha.yaml \
     --host 0.0.0.0 --port 8000
   ```

2. Open the dashboard:
   ```
   http://localhost:8000/chart
   ```

## 📊 API Endpoints

### Chart Data
- `GET /api/chart/data?symbol=GOLDGUINEA&timeframe=1m&bars=500`
- Returns historical OHLC data for chart display

### Indicators
- `GET /api/chart/indicators?strategy=sma_fractal_scalper&timeframe=1m`
- Returns SMA values, fractal points, and trade signals

### WebSocket
- `ws://localhost:8000/ws/chart`
- Real-time updates for bars, indicators, and signals

## 🎮 Controls

### Timeframe Switching
- Click timeframe buttons: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d
- Keyboard shortcuts: 1, 3, 5, q, w, h, d

### Chart Controls
- **Fit Content** (F): Auto-fit chart to data
- **Screenshot** (S): Save chart as PNG
- **Fullscreen**: Toggle fullscreen mode

### Indicator Toggles
- Click indicator toggles to show/hide
- Color-coded by indicator type
- Real-time visibility updates

## 🔄 Real-Time Events

The dashboard subscribes to these WebSocket events:

### Connection Events
```json
{
  "type": "connection",
  "data": {"status": "connected"},
  "timestamp": "2025-07-02T22:00:00"
}
```

### Bar Updates
```json
{
  "type": "bar_update",
  "data": {
    "symbol": "GOLDGUINEA",
    "timeframe": "1m",
    "bar": {
      "timestamp": "2025-07-02T22:00:00",
      "open": 895.0,
      "high": 897.0,
      "low": 893.0,
      "close": 895.5,
      "volume": 1000
    }
  }
}
```

### Indicator Updates
```json
{
  "type": "indicator_update",
  "data": {
    "sma_5": 895.2,
    "sma_200": 894.8
  }
}
```

### Signal Generation
```json
{
  "type": "signal_generated",
  "data": {
    "direction": "LONG",
    "entry_price": 895.5,
    "timestamp": "2025-07-02T22:00:00"
  }
}
```

## 🎨 Customization

### Settings Modal
- Update frequency (100ms - 10s)
- Chart theme (Dark/Light)
- Auto-fit chart option
- Settings saved to localStorage

### Keyboard Shortcuts
- `F`: Fit chart content
- `S`: Take screenshot
- `ESC`: Close modals
- `1,3,5,q,w,h,d`: Switch timeframes

## 🔧 Development

### Module Structure
- **DataService**: Handles WebSocket connections and API calls
- **ChartManager**: Manages TradingView chart and data display
- **IndicatorManager**: Handles strategy indicators and signals
- **TimeframeManager**: Manages multiple timeframe switching

### Adding New Indicators
1. Update `IndicatorManager.js` with new indicator logic
2. Add API endpoint for indicator data
3. Update chart display in `ChartManager.js`
4. Add UI controls in HTML template

### Performance Optimization
- Smart caching for timeframe data
- Throttled WebSocket updates
- Efficient chart data management
- Background preloading of adjacent timeframes

## 🚨 Error Handling

### Connection Issues
- Automatic WebSocket reconnection with exponential backoff
- Connection status indicator in header
- Error messages with auto-dismiss

### Data Loading
- Loading states during timeframe switches
- Error messages for failed API calls
- Graceful fallbacks for missing data

## 📱 Responsive Design

- Optimized for desktop trading workstations
- Responsive layout for different screen sizes
- Mobile-friendly controls and interactions
- Dark theme optimized for extended use

## 🔮 Future Enhancements

- [ ] Multiple instrument support
- [ ] Custom indicator builder
- [ ] Advanced order management
- [ ] Performance analytics dashboard
- [ ] Alert system with notifications
- [ ] Strategy backtesting integration
- [ ] Portfolio management features
- [ ] Risk management controls

## 📝 Notes

This dashboard is specifically designed for the **SMA Fractal Scalper** strategy but can be extended to support other trading strategies by modifying the indicator configurations and API endpoints. 