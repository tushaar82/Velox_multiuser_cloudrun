import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import { PlayArrow, Pause, Stop } from '@mui/icons-material';
import type { ActiveStrategy } from '../../types';
import { useAppDispatch } from '../../store/hooks';
import { pauseStrategy, resumeStrategy, stopStrategy } from '../../store/slices/strategySlice';

interface StrategyListProps {
  strategies: ActiveStrategy[];
  loading: boolean;
}

export default function StrategyList({ strategies, loading }: StrategyListProps) {
  const dispatch = useAppDispatch();

  const handlePauseStrategy = (strategyId: string) => {
    dispatch(pauseStrategy(strategyId));
  };

  const handleResumeStrategy = (strategyId: string) => {
    dispatch(resumeStrategy(strategyId));
  };

  const handleStopStrategy = (strategyId: string) => {
    if (window.confirm('Are you sure you want to stop this strategy? This action cannot be undone.')) {
      dispatch(stopStrategy(strategyId));
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'paused':
        return 'warning';
      case 'stopped':
        return 'default';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Loading strategies...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Active Strategies ({strategies.length})
      </Typography>
      {strategies.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No active strategies. Go to Strategies page to activate one.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Strategy ID</TableCell>
                <TableCell>Trading Mode</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Started At</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {strategies.map((strategy) => (
                <TableRow key={strategy.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {strategy.strategyId.substring(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={strategy.tradingMode === 'paper' ? 'Paper' : 'Live'}
                      color={strategy.tradingMode === 'paper' ? 'info' : 'success'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={strategy.status.toUpperCase()}
                      color={getStatusColor(strategy.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(strategy.startedAt).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {strategy.status === 'running' && (
                      <Tooltip title="Pause Strategy">
                        <IconButton
                          size="small"
                          color="warning"
                          onClick={() => handlePauseStrategy(strategy.id)}
                        >
                          <Pause fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {strategy.status === 'paused' && (
                      <Tooltip title="Resume Strategy">
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => handleResumeStrategy(strategy.id)}
                        >
                          <PlayArrow fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {(strategy.status === 'running' || strategy.status === 'paused') && (
                      <Tooltip title="Stop Strategy">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleStopStrategy(strategy.id)}
                        >
                          <Stop fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
