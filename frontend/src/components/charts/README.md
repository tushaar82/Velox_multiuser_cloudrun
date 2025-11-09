# Live Charting Components

This directory contains the live charting components for the algorithmic trading platform, built with TradingView Lightweight Charts library.

## Components

### LiveChart
A basic live charting component with real-time candlestick updates.

**Features:**
- Real-time tick-by-tick candle updates
- Symbol and timeframe selection
- WebSocket subscription for market data
- Position markers showing entry points
- Connection status indicator

**Usage:**
```tsx
import { LiveChart } from '../components/charts';

<LiveChart accountId={accountId} positions={positions} />
```

### LiveChartWithIndicators
An enhanced charting component with technical indicator overlays.

**Features:**
- All features from LiveChart
- Dynamic indicator overlay controls
- Support for multiple indicators:
  - Simple Moving Average (SMA)
  - Exponential Moving Average (EMA)
  - Relative Strength Index (RSI)
  - MACD
  - Bollinger Bands
- Real-time indicator value updates
- Configurable indicator parameters
- Add/remove indicators dynamically

**Usage:**
```tsx
import { LiveChartWithIndicators } from '../components/charts';

<LiveChartWithIndicators accountId={accountId} positions={positions} />
```

### IndicatorControls
A control panel for managing technical indicators on the chart.

**Features:**
- Add indicators from available list
- Toggle indicators on/off
- Configure indicator parameters
- Remove indicators
- Visual color coding for each indicator

## Implementation Details

### WebSocket Integration
The charts subscribe to market data through the WebSocket service:
- `subscribe_chart` event: Subscribe to symbol/timeframe
- `tick_update` event: Receive real-time tick updates
- `candle_complete` event: Receive completed candles
- `indicator_update` event: Receive indicator values

### Data Flow
1. User selects symbol and timeframe
2. Component subscribes to WebSocket for that symbol/timeframe
3. Initial historical data is loaded and displayed
4. Forming candle updates tick-by-tick in real-time
5. When candle completes, it's added to historical data
6. Indicators are calculated and overlaid on the chart

### Position Markers
Open positions are displayed as markers on the chart:
- Long positions: Green arrow pointing up below the candle
- Short positions: Red arrow pointing down above the candle
- Marker text shows entry price

## Supported Timeframes
- 1 Minute (1m)
- 3 Minutes (3m)
- 5 Minutes (5m)
- 15 Minutes (15m)
- 30 Minutes (30m)
- 1 Hour (1h)
- 1 Day (1d)

## Supported Symbols
Default symbols include major NSE stocks:
- RELIANCE
- TCS
- INFY
- HDFCBANK
- ICICIBANK
- SBIN
- BHARTIARTL
- ITC
- KOTAKBANK
- LT

## Technical Details

### Dependencies
- `lightweight-charts` v5.0.9: Core charting library
- `@mui/material`: UI components
- `socket.io-client`: WebSocket communication

### Chart Configuration
- Dark theme optimized for trading
- Candlestick colors: Green (up), Red (down)
- Auto-resizing on window resize
- Crosshair for precise price/time reading
- Time scale with visible timestamps

## Integration

The LiveChartWithIndicators component is integrated into the DashboardPage and displays below the portfolio summary, providing traders with real-time market visualization alongside their positions and orders.
