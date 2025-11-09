import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  MenuItem,
  LinearProgress,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Stack,
} from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import Plot from 'react-plotly.js';
import { apiClient } from '../services/api';
import type { BacktestConfig, BacktestResult } from '../types';

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<any[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [config, setConfig] = useState<Partial<BacktestConfig>>({
    symbols: ['NIFTY'],
    timeframes: ['5m'],
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    initialCapital: 100000,
    slippage: 0.05,
    commission: 0.03,
  });
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [backtestId, setBacktestId] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backtestHistory, setBacktestHistory] = useState<any[]>([]);

  useEffect(() => {
    loadStrategies();
  }, []);

  useEffect(() => {
    if (selectedStrategy) {
      loadBacktestHistory(selectedStrategy);
    }
  }, [selectedStrategy]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isRunning && backtestId) {
      interval = setInterval(async () => {
        try {
          const status = await apiClient.getBacktestStatus(backtestId);
          if (status.status === 'completed') {
            const results = await apiClient.getBacktestResults(backtestId);
            setResult(results);
            setIsRunning(false);
            setProgress(100);
            loadBacktestHistory(selectedStrategy);
          } else if (status.status === 'failed') {
            setError('Backtest failed. Please try again.');
            setIsRunning(false);
          } else if (status.progress) {
            setProgress(status.progress);
          }
        } catch (err: any) {
          console.error('Error checking backtest status:', err);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, backtestId, selectedStrategy]);

  const loadStrategies = async () => {
    try {
      const data = await apiClient.listStrategies();
      setStrategies(data);
    } catch (err: any) {
      setError('Failed to load strategies');
    }
  };

  const loadBacktestHistory = async (strategyId: string) => {
    try {
      const data = await apiClient.listBacktests(strategyId);
      setBacktestHistory(data);
    } catch (err: any) {
      console.error('Failed to load backtest history:', err);
    }
  };

  const handleStartBacktest = async () => {
    if (!selectedStrategy) {
      setError('Please select a strategy');
      return;
    }

    setError(null);
    setResult(null);
    setIsRunning(true);
    setProgress(0);

    try {
      const backtestConfig: BacktestConfig = {
        strategyId: selectedStrategy,
        symbols: config.symbols || ['NIFTY'],
        timeframes: config.timeframes || ['5m'],
        startDate: config.startDate || '',
        endDate: config.endDate || '',
        initialCapital: config.initialCapital || 100000,
        slippage: config.slippage || 0.05,
        commission: config.commission || 0.03,
      };

      const response = await apiClient.startBacktest(backtestConfig);
      setBacktestId(response.backtest_id);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to start backtest');
      setIsRunning(false);
    }
  };

  const handleActivateInPaperTrading = async () => {
    if (!result) return;

    try {
      const accountId = localStorage.getItem('account_id');
      if (!accountId) {
        setError('Account ID not found');
        return;
      }

      await apiClient.activateStrategy(accountId, result.config.strategyId, {
        trading_mode: 'paper',
        symbols: result.config.symbols,
        timeframes: result.config.timeframes,
        parameters: {},
      });

      alert('Strategy activated in paper trading mode!');
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to activate strategy');
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Backtesting
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Configuration Form */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '0 0 33%' } }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Backtest Configuration
            </Typography>

            <TextField
              select
              fullWidth
              label="Strategy"
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              margin="normal"
              disabled={isRunning}
            >
              {strategies.map((strategy) => (
                <MenuItem key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              fullWidth
              label="Symbols (comma-separated)"
              value={config.symbols?.join(', ')}
              onChange={(e) =>
                setConfig({
                  ...config,
                  symbols: e.target.value.split(',').map((s) => s.trim()),
                })
              }
              margin="normal"
              disabled={isRunning}
            />

            <TextField
              fullWidth
              label="Timeframes (comma-separated)"
              value={config.timeframes?.join(', ')}
              onChange={(e) =>
                setConfig({
                  ...config,
                  timeframes: e.target.value.split(',').map((s) => s.trim()),
                })
              }
              margin="normal"
              disabled={isRunning}
              helperText="e.g., 1m, 5m, 15m"
            />

            <TextField
              fullWidth
              type="date"
              label="Start Date"
              value={config.startDate}
              onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
              margin="normal"
              disabled={isRunning}
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              fullWidth
              type="date"
              label="End Date"
              value={config.endDate}
              onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
              margin="normal"
              disabled={isRunning}
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              fullWidth
              type="number"
              label="Initial Capital (₹)"
              value={config.initialCapital}
              onChange={(e) =>
                setConfig({ ...config, initialCapital: parseFloat(e.target.value) })
              }
              margin="normal"
              disabled={isRunning}
            />

            <TextField
              fullWidth
              type="number"
              label="Slippage (%)"
              value={config.slippage}
              onChange={(e) => setConfig({ ...config, slippage: parseFloat(e.target.value) })}
              margin="normal"
              disabled={isRunning}
              inputProps={{ step: 0.01 }}
            />

            <TextField
              fullWidth
              type="number"
              label="Commission (%)"
              value={config.commission}
              onChange={(e) => setConfig({ ...config, commission: parseFloat(e.target.value) })}
              margin="normal"
              disabled={isRunning}
              inputProps={{ step: 0.01 }}
            />

            <Button
              fullWidth
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleStartBacktest}
              disabled={isRunning || !selectedStrategy}
              sx={{ mt: 2 }}
            >
              {isRunning ? 'Running...' : 'Start Backtest'}
            </Button>

            {isRunning && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Progress: {progress.toFixed(0)}%
                </Typography>
                <LinearProgress variant="determinate" value={progress} />
              </Box>
            )}
          </Paper>

          {/* Backtest History */}
          {backtestHistory.length > 0 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Recent Backtests
              </Typography>
              {backtestHistory.slice(0, 5).map((bt) => (
                <Box
                  key={bt.id}
                  sx={{
                    p: 1,
                    mb: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                  onClick={async () => {
                    try {
                      const results = await apiClient.getBacktestResults(bt.id);
                      setResult(results);
                    } catch (err) {
                      console.error('Failed to load backtest:', err);
                    }
                  }}
                >
                  <Typography variant="body2">
                    {new Date(bt.completed_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Return: {formatPercent(bt.metrics?.totalReturn || 0)}
                  </Typography>
                </Box>
              ))}
            </Paper>
          )}
        </Box>

        {/* Results Display */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 66%' } }}>
          {result && (
            <>
              {/* Performance Metrics */}
              <Paper sx={{ p: 3, mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">Performance Metrics</Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleActivateInPaperTrading}
                  >
                    Activate in Paper Trading
                  </Button>
                </Box>

                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' }, gap: 2 }}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Total Return
                      </Typography>
                      <Typography variant="h6" color={result.metrics.totalReturn >= 0 ? 'success.main' : 'error.main'}>
                        {formatPercent(result.metrics.totalReturn)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Sharpe Ratio
                      </Typography>
                      <Typography variant="h6">
                        {result.metrics.sharpeRatio.toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Max Drawdown
                      </Typography>
                      <Typography variant="h6" color="error.main">
                        {formatPercent(result.metrics.maxDrawdown)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Win Rate
                      </Typography>
                      <Typography variant="h6">
                        {formatPercent(result.metrics.winRate)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Profit Factor
                      </Typography>
                      <Typography variant="h6">
                        {result.metrics.profitFactor.toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Total Trades
                      </Typography>
                      <Typography variant="h6">
                        {result.metrics.totalTrades}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Avg Win
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {formatCurrency(result.metrics.averageWin)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Avg Loss
                      </Typography>
                      <Typography variant="h6" color="error.main">
                        {formatCurrency(result.metrics.averageLoss)}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography color="text.secondary" variant="body2">
                        Sortino Ratio
                      </Typography>
                      <Typography variant="h6">
                        {result.metrics.sortinoRatio.toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              </Paper>

              {/* Equity Curve Chart */}
              <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Equity Curve
                </Typography>
                <Plot
                  data={[
                    {
                      x: result.equityCurve.map((point) => point.timestamp),
                      y: result.equityCurve.map((point) => point.equity),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Equity',
                      line: { color: '#1976d2', width: 2 },
                    } as any,
                  ]}
                  layout={{
                    autosize: true,
                    height: 400,
                    margin: { l: 60, r: 40, t: 40, b: 60 },
                    xaxis: {
                      title: { text: 'Date' },
                      type: 'date',
                    },
                    yaxis: {
                      title: { text: 'Equity (₹)' },
                      tickformat: ',.0f',
                    },
                    hovermode: 'x unified',
                  }}
                  config={{ responsive: true }}
                  style={{ width: '100%' }}
                />
              </Paper>

              {/* Drawdown Chart */}
              <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Drawdown
                </Typography>
                <Plot
                  data={[
                    {
                      x: result.equityCurve.map((point) => point.timestamp),
                      y: result.equityCurve.map((point) => point.drawdown * 100),
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Drawdown',
                      fill: 'tozeroy',
                      line: { color: '#d32f2f', width: 2 },
                    } as any,
                  ]}
                  layout={{
                    autosize: true,
                    height: 300,
                    margin: { l: 60, r: 40, t: 40, b: 60 },
                    xaxis: {
                      title: { text: 'Date' },
                      type: 'date',
                    },
                    yaxis: {
                      title: { text: 'Drawdown (%)' },
                      tickformat: '.2f',
                    },
                    hovermode: 'x unified',
                  }}
                  config={{ responsive: true }}
                  style={{ width: '100%' }}
                />
              </Paper>

              {/* Trade List */}
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Trade History ({result.trades.length} trades)
                </Typography>
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Entry Date</TableCell>
                        <TableCell>Exit Date</TableCell>
                        <TableCell>Symbol</TableCell>
                        <TableCell>Side</TableCell>
                        <TableCell align="right">Entry Price</TableCell>
                        <TableCell align="right">Exit Price</TableCell>
                        <TableCell align="right">Quantity</TableCell>
                        <TableCell align="right">P&L</TableCell>
                        <TableCell align="right">P&L %</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {result.trades.map((trade, index) => (
                        <TableRow key={index} hover>
                          <TableCell>
                            {new Date(trade.entryDate).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            {new Date(trade.exitDate).toLocaleString()}
                          </TableCell>
                          <TableCell>{trade.symbol}</TableCell>
                          <TableCell>
                            <Chip
                              label={trade.side}
                              size="small"
                              color={trade.side === 'long' ? 'success' : 'error'}
                            />
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(trade.entryPrice)}
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(trade.exitPrice)}
                          </TableCell>
                          <TableCell align="right">{trade.quantity}</TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: trade.pnl >= 0 ? 'success.main' : 'error.main',
                              fontWeight: 'bold',
                            }}
                          >
                            {formatCurrency(trade.pnl)}
                          </TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: trade.pnlPercent >= 0 ? 'success.main' : 'error.main',
                            }}
                          >
                            {formatPercent(trade.pnlPercent)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </>
          )}

          {!result && !isRunning && (
            <Paper sx={{ p: 5, textAlign: 'center' }}>
              <Typography variant="h6" color="text.secondary">
                Configure and run a backtest to see results
              </Typography>
            </Paper>
          )}
        </Box>
      </Box>
    </Box>
  );
}
