import { Grid, Card, CardContent, Typography, Box } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import PercentIcon from '@mui/icons-material/Percent';
import type { PerformanceMetrics } from '../../types';

interface PerformanceMetricsCardsProps {
  metrics: PerformanceMetrics;
}

export default function PerformanceMetricsCards({ metrics }: PerformanceMetricsCardsProps) {
  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const formatNumber = (value: number, decimals: number = 2) => value.toFixed(decimals);

  const metricCards = [
    {
      title: 'Total Return',
      value: formatPercent(metrics.totalReturn),
      icon: metrics.totalReturn >= 0 ? <TrendingUpIcon /> : <TrendingDownIcon />,
      color: metrics.totalReturn >= 0 ? 'success.main' : 'error.main',
    },
    {
      title: 'Annualized Return',
      value: formatPercent(metrics.annualizedReturn),
      icon: <ShowChartIcon />,
      color: metrics.annualizedReturn >= 0 ? 'success.main' : 'error.main',
    },
    {
      title: 'Sharpe Ratio',
      value: formatNumber(metrics.sharpeRatio),
      icon: <ShowChartIcon />,
      color: metrics.sharpeRatio >= 1 ? 'success.main' : metrics.sharpeRatio >= 0 ? 'warning.main' : 'error.main',
    },
    {
      title: 'Sortino Ratio',
      value: formatNumber(metrics.sortinoRatio),
      icon: <ShowChartIcon />,
      color: metrics.sortinoRatio >= 1 ? 'success.main' : metrics.sortinoRatio >= 0 ? 'warning.main' : 'error.main',
    },
    {
      title: 'Max Drawdown',
      value: formatPercent(metrics.maxDrawdown),
      icon: <TrendingDownIcon />,
      color: 'error.main',
    },
    {
      title: 'Win Rate',
      value: formatPercent(metrics.winRate),
      icon: <PercentIcon />,
      color: metrics.winRate >= 0.5 ? 'success.main' : 'warning.main',
    },
    {
      title: 'Profit Factor',
      value: formatNumber(metrics.profitFactor),
      icon: <ShowChartIcon />,
      color: metrics.profitFactor >= 1.5 ? 'success.main' : metrics.profitFactor >= 1 ? 'warning.main' : 'error.main',
    },
    {
      title: 'Total Trades',
      value: metrics.totalTrades.toString(),
      icon: <ShowChartIcon />,
      color: 'primary.main',
    },
    {
      title: 'Winning Trades',
      value: metrics.winningTrades.toString(),
      icon: <TrendingUpIcon />,
      color: 'success.main',
    },
    {
      title: 'Losing Trades',
      value: metrics.losingTrades.toString(),
      icon: <TrendingDownIcon />,
      color: 'error.main',
    },
    {
      title: 'Average Win',
      value: `₹${formatNumber(metrics.averageWin)}`,
      icon: <TrendingUpIcon />,
      color: 'success.main',
    },
    {
      title: 'Average Loss',
      value: `₹${formatNumber(metrics.averageLoss)}`,
      icon: <TrendingDownIcon />,
      color: 'error.main',
    },
  ];

  return (
    <Grid container spacing={2}>
      {metricCards.map((card, index) => (
        <Grid key={index} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="text.secondary">
                  {card.title}
                </Typography>
                <Box sx={{ color: card.color }}>{card.icon}</Box>
              </Box>
              <Typography variant="h5" sx={{ color: card.color }}>
                {card.value}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
