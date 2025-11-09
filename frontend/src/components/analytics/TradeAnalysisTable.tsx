import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Box,
  Chip,
  Grid,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import type { TradeStatistics } from '../../types';

interface TradeAnalysisTableProps {
  statistics: TradeStatistics;
}

export default function TradeAnalysisTable({ statistics }: TradeAnalysisTableProps) {
  const formatDuration = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)} minutes`;
    if (hours < 24) return `${hours.toFixed(1)} hours`;
    return `${(hours / 24).toFixed(1)} days`;
  };

  const formatCurrency = (value: number) => `₹${value.toFixed(2)}`;
  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Trade Analysis
        </Typography>

        {/* Summary Stats */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Avg Holding Time
              </Typography>
              <Typography variant="h6">{formatDuration(statistics.averageHoldingTime)}</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Consecutive Wins
              </Typography>
              <Typography variant="h6" color="success.main">
                {statistics.consecutiveWins}
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Consecutive Losses
              </Typography>
              <Typography variant="h6" color="error.main">
                {statistics.consecutiveLosses}
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Best Trade
              </Typography>
              <Typography variant="h6" color="success.main">
                {formatCurrency(statistics.bestTrade.pnl)}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* Best and Worst Trades */}
        <Typography variant="subtitle1" gutterBottom sx={{ mt: 3 }}>
          Best & Worst Trades
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Side</TableCell>
                <TableCell align="right">Entry</TableCell>
                <TableCell align="right">Exit</TableCell>
                <TableCell align="right">P&L</TableCell>
                <TableCell align="right">Return</TableCell>
                <TableCell>Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>
                  <Chip
                    icon={<TrendingUpIcon />}
                    label="Best"
                    color="success"
                    size="small"
                  />
                </TableCell>
                <TableCell>{statistics.bestTrade.symbol}</TableCell>
                <TableCell>
                  <Chip
                    label={statistics.bestTrade.side.toUpperCase()}
                    size="small"
                    color={statistics.bestTrade.side === 'long' ? 'primary' : 'secondary'}
                  />
                </TableCell>
                <TableCell align="right">{formatCurrency(statistics.bestTrade.entryPrice)}</TableCell>
                <TableCell align="right">{formatCurrency(statistics.bestTrade.exitPrice)}</TableCell>
                <TableCell align="right" sx={{ color: 'success.main', fontWeight: 'bold' }}>
                  {formatCurrency(statistics.bestTrade.pnl)}
                </TableCell>
                <TableCell align="right" sx={{ color: 'success.main' }}>
                  {formatPercent(statistics.bestTrade.pnlPercent)}
                </TableCell>
                <TableCell>{new Date(statistics.bestTrade.entryDate).toLocaleDateString()}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>
                  <Chip
                    icon={<TrendingDownIcon />}
                    label="Worst"
                    color="error"
                    size="small"
                  />
                </TableCell>
                <TableCell>{statistics.worstTrade.symbol}</TableCell>
                <TableCell>
                  <Chip
                    label={statistics.worstTrade.side.toUpperCase()}
                    size="small"
                    color={statistics.worstTrade.side === 'long' ? 'primary' : 'secondary'}
                  />
                </TableCell>
                <TableCell align="right">{formatCurrency(statistics.worstTrade.entryPrice)}</TableCell>
                <TableCell align="right">{formatCurrency(statistics.worstTrade.exitPrice)}</TableCell>
                <TableCell align="right" sx={{ color: 'error.main', fontWeight: 'bold' }}>
                  {formatCurrency(statistics.worstTrade.pnl)}
                </TableCell>
                <TableCell align="right" sx={{ color: 'error.main' }}>
                  {formatPercent(statistics.worstTrade.pnlPercent)}
                </TableCell>
                <TableCell>{new Date(statistics.worstTrade.entryDate).toLocaleDateString()}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>

        {/* Profit by Time of Day */}
        <Typography variant="subtitle1" gutterBottom sx={{ mt: 3 }}>
          Profit by Time of Day
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Hour</TableCell>
                <TableCell align="right">Profit</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {statistics.profitByTimeOfDay.map((item) => (
                <TableRow key={item.hour}>
                  <TableCell>{`${item.hour}:00 - ${item.hour + 1}:00`}</TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      color: item.profit >= 0 ? 'success.main' : 'error.main',
                      fontWeight: item.profit !== 0 ? 'bold' : 'normal',
                    }}
                  >
                    {formatCurrency(item.profit)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Profit by Day of Week */}
        <Typography variant="subtitle1" gutterBottom sx={{ mt: 3 }}>
          Profit by Day of Week
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Day</TableCell>
                <TableCell align="right">Profit</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {statistics.profitByDayOfWeek.map((item) => (
                <TableRow key={item.day}>
                  <TableCell>{item.day}</TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      color: item.profit >= 0 ? 'success.main' : 'error.main',
                      fontWeight: item.profit !== 0 ? 'bold' : 'normal',
                    }}
                  >
                    {formatCurrency(item.profit)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}
