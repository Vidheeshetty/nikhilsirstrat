# TradingView Lightweight Charts™ v5.0.8 API Reference

## Overview

This document provides a comprehensive API reference for TradingView Lightweight Charts™ version 5.0.8, the library we're using for our trading dashboard. This reference is specifically tailored for our project needs.

## Installation & Setup

```bash
npm install --save lightweight-charts
```

### Build Variants Available

| Dependencies | Mode | ES Module | IIFE (window.LightweightCharts) |
|-------------|------|-----------|----------------------------------|
| Standalone  | PROD | lightweight-charts.standalone.production.mjs | lightweight-charts.standalone.production.js |
| Standalone  | DEV  | lightweight-charts.standalone.development.mjs | lightweight-charts.standalone.development.js |

**We use:** `lightweight-charts.standalone.production.js` (IIFE variant for browser)

## Core API Structure

### 1. Chart Creation

```javascript
// Create chart instance
const chart = LightweightCharts.createChart(container, options);

// Basic chart options
const chartOptions = {
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
```

### 2. Series Creation (v5.0.8 Syntax)

#### Candlestick Series
```javascript
const candlestickSeries = chart.addCandlestickSeries({
    upColor: '#4bffb5',
    downColor: '#ff4976',
    borderDownColor: '#ff4976',
    borderUpColor: '#4bffb5',
    wickDownColor: '#ff4976',
    wickUpColor: '#4bffb5',
});
```

#### Line Series
```javascript
const lineSeries = chart.addSeries('Line', {
    color: '#2196f3',
    lineWidth: 2,
});
```

#### Area Series
```javascript
const areaSeries = chart.addAreaSeries({
    topColor: 'rgba(33, 150, 243, 0.56)',
    bottomColor: 'rgba(33, 150, 243, 0.04)',
    lineColor: '#2196f3',
    lineWidth: 2,
});
```

### 3. Data Format

#### OHLC Data Structure
```javascript
const ohlcData = [
    {
        time: 1642425600, // Unix timestamp in seconds
        open: 100.0,
        high: 105.0,
        low: 98.0,
        close: 102.0,
    },
    // ... more bars
];
```

#### Line/Area Data Structure
```javascript
const lineData = [
    { time: 1642425600, value: 100.0 },
    { time: 1642429200, value: 102.0 },
    // ... more points
];
```

### 4. Setting Data

```javascript
// Set complete dataset
candlestickSeries.setData(ohlcData);
lineSeries.setData(lineData);

// Update single point (real-time)
candlestickSeries.update({
    time: 1642432800,
    open: 102.0,
    high: 104.0,
    low: 101.0,
    close: 103.0,
});
```

### 5. Time Scale Operations

```javascript
// Fit chart to content
chart.timeScale().fitContent();

// Set visible range
chart.timeScale().setVisibleRange({
    from: 1642425600,
    to: 1642432800,
});

// Get visible range
const range = chart.timeScale().getVisibleRange();

// Subscribe to visible range changes
chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
    console.log('Visible range changed:', range);
});
```

### 6. Price Scale Operations

```javascript
// Auto-scale to fit data
chart.priceScale('right').applyOptions({
    autoScale: true,
});

// Set price range
chart.priceScale('right').setVisibleRange({
    from: 95.0,
    to: 110.0,
});
```

### 7. Event Handling

#### Crosshair Events
```javascript
chart.subscribeCrosshairMove((param) => {
    if (param.time) {
        const data = param.seriesPrices.get(candlestickSeries);
        if (data) {
            console.log('OHLC:', data);
        }
    }
});
```

#### Click Events
```javascript
chart.subscribeClick((param) => {
    console.log('Chart clicked at:', param.time, param.point);
});
```

### 8. Markers and Annotations

```javascript
// Add price line
const priceLine = candlestickSeries.createPriceLine({
    price: 100.0,
    color: '#ff0000',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Resistance Level',
});

// Remove price line
candlestickSeries.removePriceLine(priceLine);
```

### 9. Chart Customization

#### Layout Options
```javascript
chart.applyOptions({
    layout: {
        background: { 
            type: 'solid', 
            color: '#1a1a1a' 
        },
        textColor: '#d1d4dc',
        fontSize: 12,
        fontFamily: 'Arial, sans-serif',
    },
});
```

#### Grid Options
```javascript
chart.applyOptions({
    grid: {
        vertLines: {
            color: '#2a2a2a',
            style: LightweightCharts.LineStyle.Solid,
            visible: true,
        },
        horzLines: {
            color: '#2a2a2a',
            style: LightweightCharts.LineStyle.Solid,
            visible: true,
        },
    },
});
```

#### Crosshair Options
```javascript
chart.applyOptions({
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: {
            color: '#9598A1',
            width: 1,
            style: LightweightCharts.LineStyle.Dashed,
            visible: true,
            labelVisible: true,
        },
        horzLine: {
            color: '#9598A1',
            width: 1,
            style: LightweightCharts.LineStyle.Dashed,
            visible: true,
            labelVisible: true,
        },
    },
});
```

## Enums and Constants

### CrosshairMode
```javascript
LightweightCharts.CrosshairMode.Normal
LightweightCharts.CrosshairMode.Magnet
LightweightCharts.CrosshairMode.Hidden
```

### LineStyle
```javascript
LightweightCharts.LineStyle.Solid
LightweightCharts.LineStyle.Dotted
LightweightCharts.LineStyle.Dashed
LightweightCharts.LineStyle.LargeDashed
LightweightCharts.LineStyle.SparseDotted
```

### PriceScaleMode
```javascript
LightweightCharts.PriceScaleMode.Normal
LightweightCharts.PriceScaleMode.Logarithmic
LightweightCharts.PriceScaleMode.Percentage
LightweightCharts.PriceScaleMode.IndexedTo100
```

## Common Patterns for Our Dashboard

### 1. Real-time Data Updates
```javascript
// WebSocket data handler
function handleRealtimeData(barData) {
    const chartBar = {
        time: Math.floor(new Date(barData.timestamp).getTime() / 1000),
        open: parseFloat(barData.open),
        high: parseFloat(barData.high),
        low: parseFloat(barData.low),
        close: parseFloat(barData.close),
    };
    
    candlestickSeries.update(chartBar);
}
```

### 2. Multiple Timeframes
```javascript
async function changeTimeframe(newTimeframe) {
    // Clear existing data
    candlestickSeries.setData([]);
    
    // Load new data
    const data = await fetchHistoricalData(symbol, newTimeframe);
    const chartData = convertToChartFormat(data);
    
    // Set new data
    candlestickSeries.setData(chartData);
    chart.timeScale().fitContent();
}
```

### 3. Technical Indicators
```javascript
// Add SMA line
function addSMA(period, data) {
    const smaData = calculateSMA(data, period);
    const smaSeries = chart.addSeries('Line', {
        color: '#ff6b35',
        lineWidth: 1,
        title: `SMA ${period}`,
    });
    smaSeries.setData(smaData);
    return smaSeries;
}
```