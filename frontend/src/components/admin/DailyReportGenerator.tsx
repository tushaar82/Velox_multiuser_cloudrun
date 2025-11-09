import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Alert,
  CircularProgress,
  Paper,
  Divider,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import {
  Download as DownloadIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { apiClient } from '../../services/api';

interface DailyReport {
  date: string;
  summary: {
    total_users: number;
    active_users: number;
    new_registrations: number;
    total_orders: number;
    paper_orders: number;
    live_orders: number;
    order_success_rate: number;
    active_strategies: number;
    total_positions: number;
    system_uptime: number;
  };
  user_activity: {
    logins: number;
    failed_logins: number;
    account_lockouts: number;
  };
  trading_activity: {
    total_volume: number;
    paper_volume: number;
    live_volume: number;
    unique_symbols_traded: number;
  };
  errors: {
    strategy_errors: number;
    broker_connection_errors: number;
    order_rejections: number;
  };
}

export function DailyReportGenerator() {
  const [selectedDate, setSelectedDate] = useState<Date | null>(
    new Date(Date.now() - 24 * 60 * 60 * 1000) // Yesterday
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<DailyReport | null>(null);
  const [downloading, setDownloading] = useState(false);

  const generateReport = async () => {
    if (!selectedDate) {
      setError('Please select a date');
      return;
    }

    try {
      setError(null);
      setLoading(true);
      const dateStr = selectedDate.toISOString().split('T')[0];
      // Create a temporary method to get daily report data
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/admin/reports/daily?date=${dateStr}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch report');
      }
      const data = await response.json();
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to generate report');
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = async () => {
    if (!selectedDate) {
      setError('Please select a date');
      return;
    }

    try {
      setError(null);
      setDownloading(true);
      const dateStr = selectedDate.toISOString().split('T')[0];
      const blob = await apiClient.generateDailyReport(dateStr);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `daily-report-${dateStr}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to download report');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Typography variant="h6" gutterBottom>
          Daily Activity Report Generator
        </Typography>

        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={4}>
              <DatePicker
                label="Report Date"
                value={selectedDate}
                onChange={(newValue) => setSelectedDate(newValue)}
                maxDate={new Date()}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<AssessmentIcon />}
                onClick={generateReport}
                disabled={loading || !selectedDate}
              >
                {loading ? 'Generating...' : 'Generate Report'}
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={downloading ? <CircularProgress size={20} /> : <DownloadIcon />}
                onClick={downloadReport}
                disabled={downloading || !selectedDate}
              >
                {downloading ? 'Downloading...' : 'Download PDF'}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
            <CircularProgress />
          </Box>
        )}

        {report && !loading && (
          <Grid container spacing={3}>
            {/* Summary Section */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Daily Summary - {new Date(report.date).toLocaleDateString()}
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={4} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Total Users
                      </Typography>
                      <Typography variant="h5">{report.summary.total_users}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Active Users
                      </Typography>
                      <Typography variant="h5">{report.summary.active_users}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        New Registrations
                      </Typography>
                      <Typography variant="h5">{report.summary.new_registrations}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        System Uptime
                      </Typography>
                      <Typography variant="h5">
                        {report.summary.system_uptime.toFixed(1)}%
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* Trading Activity */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Trading Activity
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Total Orders
                      </Typography>
                      <Typography variant="h5">{report.summary.total_orders}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Paper: {report.summary.paper_orders} | Live: {report.summary.live_orders}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Success Rate
                      </Typography>
                      <Typography variant="h5">
                        {report.summary.order_success_rate.toFixed(1)}%
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Active Strategies
                      </Typography>
                      <Typography variant="h5">{report.summary.active_strategies}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Total Positions
                      </Typography>
                      <Typography variant="h5">{report.summary.total_positions}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">
                        Unique Symbols Traded
                      </Typography>
                      <Typography variant="h5">
                        {report.trading_activity.unique_symbols_traded}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* User Activity */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    User Activity
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Successful Logins
                      </Typography>
                      <Typography variant="h5">{report.user_activity.logins}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Failed Logins
                      </Typography>
                      <Typography variant="h5" color="error">
                        {report.user_activity.failed_logins}
                      </Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">
                        Account Lockouts
                      </Typography>
                      <Typography variant="h5" color="warning.main">
                        {report.user_activity.account_lockouts}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* Errors and Issues */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Errors and Issues
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        Strategy Errors
                      </Typography>
                      <Typography variant="h5" color="error">
                        {report.errors.strategy_errors}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        Broker Connection Errors
                      </Typography>
                      <Typography variant="h5" color="error">
                        {report.errors.broker_connection_errors}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        Order Rejections
                      </Typography>
                      <Typography variant="h5" color="error">
                        {report.errors.order_rejections}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Box>
    </LocalizationProvider>
  );
}
