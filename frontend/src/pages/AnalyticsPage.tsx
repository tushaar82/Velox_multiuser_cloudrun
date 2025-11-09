import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  ToggleButtonGroup,
  ToggleButton,
  Button,
  CircularProgress,
  Alert,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import {
  PerformanceMetricsCards,
  EquityCurveChart,
  DrawdownChart,
  StrategyBreakdownChart,
  TradeAnalysisTable,
} from '../components/analytics';
import { apiClient } from '../services/api';
import type {
  PerformanceMetrics,
  EquityPoint,
  StrategyPerformance,
  TradeStatistics,
  TradingMode,
} from '../types';

type Period = 'daily' | 'weekly' | 'monthly' | 'yearly' | 'all';

export default function AnalyticsPage() {
  const [tradingMode, setTradingMode] = useState<TradingMode>('paper');
  const [period, setPeriod] = useState<Period>('monthly');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Data state
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [strategyBreakdown, setStrategyBreakdown] = useState<StrategyPerformance[]>([]);
  const [tradeStatistics, setTradeStatistics] = useState<TradeStatistics | null>(null);

  // Get account ID from auth state (you may need to adjust this based on your auth implementation)
  const accountId = localStorage.getItem('account_id') || 'default-account';

  useEffect(() => {
    loadAnalyticsData();
  }, [tradingMode, period]);

  const loadAnalyticsData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Calculate date range based on period
      const endDate = new Date();
      const startDate = new Date();
      
      switch (period) {
        case 'daily':
          startDate.setDate(endDate.getDate() - 1);
          break;
        case 'weekly':
          startDate.setDate(endDate.getDate() - 7);
          break;
        case 'monthly':
          startDate.setMonth(endDate.getMonth() - 1);
          break;
        case 'yearly':
          startDate.setFullYear(endDate.getFullYear() - 1);
          break;
        case 'all':
          startDate.setFullYear(2020, 0, 1); // Start from 2020
          break;
      }

      // Fetch all analytics data in parallel
      const [metricsData, equityCurveData, strategyBreakdownData, tradeAnalysisData] = await Promise.all([
        apiClient.getPerformanceMetrics(accountId, tradingMode, period),
        apiClient.getEquityCurve(
          accountId,
          tradingMode,
          startDate.toISOString(),
          endDate.toISOString()
        ),
        apiClient.getStrategyBreakdown(accountId, tradingMode),
        apiClient.getTradeAnalysis(accountId, tradingMode),
      ]);

      setMetrics(metricsData);
      setEquityCurve(equityCurveData);
      setStrategyBreakdown(strategyBreakdownData);
      setTradeStatistics(tradeAnalysisData);
    } catch (err: any) {
      console.error('Failed to load analytics data:', err);
      setError(err.response?.data?.message || 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'csv') => {
    setExporting(true);
    try {
      const blob = await apiClient.exportReport(accountId, tradingMode, format);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `analytics-report-${tradingMode}-${period}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to export report:', err);
      setError(err.response?.data?.message || 'Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Analytics Dashboard</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={exporting ? <CircularProgress size={16} /> : <DownloadIcon />}
            onClick={() => handleExport('pdf')}
            disabled={exporting || loading || !metrics}
          >
            Export PDF
          </Button>
          <Button
            variant="outlined"
            startIcon={exporting ? <CircularProgress size={16} /> : <DownloadIcon />}
            onClick={() => handleExport('csv')}
            disabled={exporting || loading || !metrics}
          >
            Export CSV
          </Button>
        </Box>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Trading Mode
              </Typography>
              <ToggleButtonGroup
                value={tradingMode}
                exclusive
                onChange={(_, value) => value && setTradingMode(value)}
                size="small"
                fullWidth
              >
                <ToggleButton value="paper">Paper Trading</ToggleButton>
                <ToggleButton value="live">Live Trading</ToggleButton>
              </ToggleButtonGroup>
            </Box>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Period</InputLabel>
              <Select
                value={period}
                label="Period"
                onChange={(e) => setPeriod(e.target.value as Period)}
              >
                <MenuItem value="daily">Daily</MenuItem>
                <MenuItem value="weekly">Weekly</MenuItem>
                <MenuItem value="monthly">Monthly</MenuItem>
                <MenuItem value="yearly">Yearly</MenuItem>
                <MenuItem value="all">All Time</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      )}

      {/* Analytics Content */}
      {!loading && metrics && (
        <Box>
          {/* Performance Metrics Cards */}
          <Box mb={3}>
            <PerformanceMetricsCards metrics={metrics} />
          </Box>

          {/* Equity Curve and Drawdown Charts */}
          <Grid container spacing={3} mb={3}>
            <Grid item xs={12} lg={6}>
              <EquityCurveChart data={equityCurve} />
            </Grid>
            <Grid item xs={12} lg={6}>
              <DrawdownChart data={equityCurve} />
            </Grid>
          </Grid>

          {/* Strategy Breakdown */}
          {strategyBreakdown.length > 0 && (
            <Box mb={3}>
              <StrategyBreakdownChart data={strategyBreakdown} />
            </Box>
          )}

          {/* Trade Analysis */}
          {tradeStatistics && (
            <Box mb={3}>
              <TradeAnalysisTable statistics={tradeStatistics} />
            </Box>
          )}
        </Box>
      )}

      {/* No Data State */}
      {!loading && !metrics && !error && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Analytics Data Available
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Start trading to see your performance analytics here.
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
