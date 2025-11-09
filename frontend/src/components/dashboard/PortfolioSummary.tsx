import { Box, Card, CardContent, Typography, Chip } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';
import type { DashboardSummary, TradingMode } from '../../types';

interface PortfolioSummaryProps {
  summary: DashboardSummary | null;
  tradingMode: TradingMode;
  loading: boolean;
}

export default function PortfolioSummary({ summary, tradingMode, loading }: PortfolioSummaryProps) {
  if (loading || !summary) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Loading portfolio summary...
        </Typography>
      </Box>
    );
  }

  const isProfitable = summary.dailyPnl >= 0;

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ flexGrow: 1 }}>
          Portfolio Summary
        </Typography>
        <Chip
          label={tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
          color={tradingMode === 'paper' ? 'info' : 'success'}
          size="small"
        />
      </Box>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Equity
              </Typography>
              <Typography variant="h5">
                ₹{summary.equity.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Typography>
            </CardContent>
          </Card>
        </Box>
        <Box sx={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Daily P&L
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography
                  variant="h5"
                  sx={{ color: isProfitable ? 'success.main' : 'error.main', mr: 1 }}
                >
                  ₹{summary.dailyPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </Typography>
                {isProfitable ? (
                  <TrendingUp color="success" />
                ) : (
                  <TrendingDown color="error" />
                )}
              </Box>
            </CardContent>
          </Card>
        </Box>
        <Box sx={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Active Strategies
              </Typography>
              <Typography variant="h5">{summary.activeStrategies}</Typography>
            </CardContent>
          </Card>
        </Box>
        <Box sx={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Open Positions
              </Typography>
              <Typography variant="h5">{summary.openPositions}</Typography>
            </CardContent>
          </Card>
        </Box>
        <Box sx={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Today's Orders
              </Typography>
              <Typography variant="h5">{summary.todayOrders}</Typography>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  );
}
