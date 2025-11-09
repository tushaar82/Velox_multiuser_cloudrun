import { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  LinearProgress,
  Chip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  ShoppingCart as OrdersIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { apiClient } from '../../services/api';

interface SystemHealthData {
  users: {
    total_active: number;
    by_role: {
      admin: number;
      trader: number;
      investor: number;
    };
  };
  orders: {
    total: number;
    paper: number;
    live: number;
    success_rate: number;
  };
  resources: {
    cpu_usage: number;
    memory_usage: number;
    database_connections: number;
    redis_memory_mb: number;
  };
  trading: {
    active_strategies: number;
    paper_strategies: number;
    live_strategies: number;
    total_positions: number;
  };
  timestamp: string;
}

export function SystemHealthOverview() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);

  const fetchHealthData = async () => {
    try {
      setError(null);
      const data = await apiClient.getSystemHealth();
      setHealthData(data);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch system health data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchHealthData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!healthData) {
    return <Alert severity="info">No health data available</Alert>;
  }

  const getStatusColor = (value: number, threshold: number) => {
    if (value >= threshold) return 'error';
    if (value >= threshold * 0.8) return 'warning';
    return 'success';
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">System Health Overview</Typography>
        <Typography variant="caption" color="text.secondary">
          Last updated: {new Date(healthData.timestamp).toLocaleString()}
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Active Users */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <PeopleIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  Active Users
                </Typography>
              </Box>
              <Typography variant="h3" component="div" gutterBottom>
                {healthData.users.total_active}
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip label={`Admin: ${healthData.users.by_role.admin}`} size="small" />
                <Chip label={`Trader: ${healthData.users.by_role.trader}`} size="small" />
                <Chip label={`Investor: ${healthData.users.by_role.investor}`} size="small" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Orders Processed */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <OrdersIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  Orders Today
                </Typography>
              </Box>
              <Typography variant="h3" component="div" gutterBottom>
                {healthData.orders.total}
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip label={`Paper: ${healthData.orders.paper}`} size="small" color="info" />
                <Chip label={`Live: ${healthData.orders.live}`} size="small" color="success" />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Success Rate: {healthData.orders.success_rate.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Strategies */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <TrendingUpIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  Active Strategies
                </Typography>
              </Box>
              <Typography variant="h3" component="div" gutterBottom>
                {healthData.trading.active_strategies}
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip label={`Paper: ${healthData.trading.paper_strategies}`} size="small" color="info" />
                <Chip label={`Live: ${healthData.trading.live_strategies}`} size="small" color="success" />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Positions: {healthData.trading.total_positions}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* System Resources */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SpeedIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  System Load
                </Typography>
              </Box>
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={0.5}>
                  <Typography variant="body2">CPU</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {healthData.resources.cpu_usage.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthData.resources.cpu_usage}
                  color={getStatusColor(healthData.resources.cpu_usage, 80)}
                />
              </Box>
              <Box>
                <Box display="flex" justifyContent="space-between" mb={0.5}>
                  <Typography variant="body2">Memory</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {healthData.resources.memory_usage.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthData.resources.memory_usage}
                  color={getStatusColor(healthData.resources.memory_usage, 90)}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Database & Cache */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MemoryIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  Database & Cache
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    DB Connections
                  </Typography>
                  <Typography variant="h4">
                    {healthData.resources.database_connections}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    / 100 max
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Redis Memory
                  </Typography>
                  <Typography variant="h4">
                    {healthData.resources.redis_memory_mb.toFixed(0)} MB
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    / 5120 MB max
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Order Success Rate */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="div" gutterBottom>
                Order Execution Performance
              </Typography>
              <Box mt={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Success Rate</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {healthData.orders.success_rate.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthData.orders.success_rate}
                  color={getStatusColor(100 - healthData.orders.success_rate, 10)}
                  sx={{ height: 10, borderRadius: 5 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {healthData.orders.total} orders processed today
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
