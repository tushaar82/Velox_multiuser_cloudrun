import React, { useEffect, useRef, useState } from 'react';
import { createChart, type Time } from 'lightweight-charts';
import { Box, FormControl, InputLabel, Select, MenuItem, Paper, Typography, Chip } from '@mui/material';
import { wsService } from '../../services/websocket';
import type { Candle, Position } from '../../types';

interface LiveChartProps {
  accountId: string;
  positions?: Position[];
}

interface ChartData {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
}

const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '3m', label: '3 Minutes' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '1d', label: '1 Day' },
];

const SYMBOLS = [
  'RELIANCE',
  'TCS',
  'INFY',
  'HDFCBANK',
  'ICICIBANK',
  'SBIN',
  'BHARTIARTL',
  'ITC',
  'KOTAKBANK',
  'LT',
];

export const LiveChart: React.FC<LiveChartProps> = ({ positions = [] }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
  const [symbol, setSymbol] = useState('RELIANCE');
  const [timeframe, setTimeframe] = useState('5m');
  const [isConnected, setIsConnected] = useState(false);
  const formingCandleRef = useRef<ChartData | null>(null);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: '#1e1e1e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2b2b43' },
        horzLines: { color: '#2b2b43' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#2b2b43',
      },
      timeScale: {
        borderColor: '#2b2b43',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = (chart as any).addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    // Handle window resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Subscribe to market data
  useEffect(() => {
    if (!wsService.isConnected()) {
      setIsConnected(false);
      return;
    }

    setIsConnected(true);

    const handleMarketData = (data: any) => {
      if (data.symbol !== symbol || data.timeframe !== timeframe) return;

      if (data.type === 'historical') {
        // Initial historical data
        const historicalCandles: ChartData[] = data.candles.map((candle: Candle) => ({
          time: (new Date(candle.timestamp).getTime() / 1000) as Time,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        }));
        if (candleSeriesRef.current) {
          candleSeriesRef.current.setData(historicalCandles);
        }
      } else if (data.type === 'tick_update') {
        // Update forming candle with tick data
        updateFormingCandle(data.candle);
      } else if (data.type === 'candle_complete') {
        // Candle completed, add to historical data
        const completedCandle: ChartData = {
          time: (new Date(data.candle.timestamp).getTime() / 1000) as Time,
          open: data.candle.open,
          high: data.candle.high,
          low: data.candle.low,
          close: data.candle.close,
        };
        
        if (candleSeriesRef.current) {
          candleSeriesRef.current.update(completedCandle);
        }
        
        formingCandleRef.current = null;
      }
    };

    wsService.subscribeToChart(symbol, timeframe, handleMarketData);

    return () => {
      wsService.unsubscribeFromChart(symbol, timeframe);
    };
  }, [symbol, timeframe]);

  // Update forming candle tick-by-tick
  const updateFormingCandle = (candle: Candle) => {
    const candleTime = (new Date(candle.timestamp).getTime() / 1000) as Time;
    const newCandle: ChartData = {
      time: candleTime,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    };

    if (formingCandleRef.current) {
      // Update existing forming candle
      if (candleSeriesRef.current) {
        candleSeriesRef.current.update(newCandle);
      }
    } else {
      // First tick of new forming candle
      if (candleSeriesRef.current) {
        candleSeriesRef.current.update(newCandle);
      }
    }

    formingCandleRef.current = newCandle;
  };

  // Add position markers on chart
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;

    const markers = positions
      .filter((pos) => pos.symbol === symbol)
      .map((pos) => {
        const time = (new Date(pos.openedAt).getTime() / 1000) as Time;
        return {
          time,
          position: pos.side === 'long' ? ('belowBar' as const) : ('aboveBar' as const),
          color: pos.side === 'long' ? '#26a69a' : '#ef5350',
          shape: pos.side === 'long' ? ('arrowUp' as const) : ('arrowDown' as const),
          text: `${pos.side.toUpperCase()} @ ${pos.entryPrice}`,
        };
      });

    try {
      if ('setMarkers' in candleSeriesRef.current) {
        (candleSeriesRef.current as any).setMarkers(markers);
      }
    } catch (error) {
      console.warn('Failed to set markers:', error);
    }
  }, [positions, symbol]);

  const handleSymbolChange = (event: any) => {
    setSymbol(event.target.value);
    formingCandleRef.current = null;
  };

  const handleTimeframeChange = (event: any) => {
    setTimeframe(event.target.value);
    formingCandleRef.current = null;
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Live Chart</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Chip
            label={isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Symbol</InputLabel>
            <Select value={symbol} label="Symbol" onChange={handleSymbolChange}>
              {SYMBOLS.map((sym) => (
                <MenuItem key={sym} value={sym}>
                  {sym}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select value={timeframe} label="Timeframe" onChange={handleTimeframeChange}>
              {TIMEFRAMES.map((tf) => (
                <MenuItem key={tf.value} value={tf.value}>
                  {tf.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Box>
      <Box ref={chartContainerRef} sx={{ width: '100%', height: 500 }} />
    </Paper>
  );
};
