import { useEffect } from 'react';
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import type { TradingMode } from '../../types';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import {
  fetchActiveStrategies,
  pauseStrategy,
  resumeStrategy,
  stopStrategy,
} from '../../store/slices/strategySlice';

interface ActiveStrategyMonitorProps {
  accountId: string;
  tradingMode?: TradingMode;
}

export default function ActiveStrategyMonitor({
  accountId,
  tradingMode,
}: ActiveStrategyMonitorProps) {
  const dispatch = useAppDispatch();
  const { activeStrategies, strategies } = useAppSelector((state) => state.strategy);

  useEffect(() => {
    dispatch(fetchActiveStrategies({ accountId, tradingMode }));

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      dispatch(fetchActiveStrategies({ accountId, tradingMode }));
    }, 5000);

    return () => clearInterval(interval);
  }, [dispatch, accountId, tradingMode]);

  const handlePause = (strategyId: string) => {
    dispatch(pauseStrategy(strategyId));
  };

  const handleResume = (strategyId: string) => {
    dispatch(resumeStrategy(strategyId));
  };

  const handleStop = (strategyId: string) => {
    if (window.confirm('Are you sure you want to stop this strategy? This action cannot be undone.')) {
      dispatch(stopStrategy(strategyId));
    }
  };

  const getStrategyName = (strategyId: string) => {
    const strategy = strategies.find((s) => s.id === strategyId);
    return strategy?.name || 'Unknown Strategy';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'paused':
        return 'warning';
      case 'error':
        return 'error';
      case 'stopped':
        return 'default';
      default:
        return 'default';
    }
  };

  const getTradingModeColor = (mode: TradingMode) => {
    return mode === 'live' ? 'error' : 'info';
  };

  if (activeStrategies.length === 0) {
    return (
      <Alert severity="info">
        No active strategies. Activate a strategy from the Strategy Library to get started.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Active Strategies
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Strategy</TableCell>
              <TableCell>Trading Mode</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Started At</TableCell>
              <TableCell>Symbols</TableCell>
              <TableCell>Timeframes</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {activeStrategies.map((activeStrategy) => (
              <TableRow key={activeStrategy.id}>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {getStrategyName(activeStrategy.strategyId)}
                  </Typography>
                </TableCell>

                <TableCell>
                  <Chip
                    label={activeStrategy.tradingMode.toUpperCase()}
                    color={getTradingModeColor(activeStrategy.tradingMode)}
                    size="small"
                  />
                </TableCell>

                <TableCell>
                  <Chip
                    label={activeStrategy.status.toUpperCase()}
                    color={getStatusColor(activeStrategy.status)}
                    size="small"
                    icon={activeStrategy.status === 'error' ? <ErrorIcon /> : undefined}
                  />
                </TableCell>

                <TableCell>
                  <Typography variant="body2">
                    {new Date(activeStrategy.startedAt).toLocaleString('en-US', {
                      month: 'short',
                      day: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </Typography>
                </TableCell>

                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {activeStrategy.config.symbols?.slice(0, 2).map((symbol: string) => (
                      <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                    ))}
                    {activeStrategy.config.symbols?.length > 2 && (
                      <Chip
                        label={`+${activeStrategy.config.symbols.length - 2}`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </TableCell>

                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {activeStrategy.config.timeframes?.slice(0, 2).map((tf: string) => (
                      <Chip key={tf} label={tf} size="small" />
                    ))}
                    {activeStrategy.config.timeframes?.length > 2 && (
                      <Chip
                        label={`+${activeStrategy.config.timeframes.length - 2}`}
                        size="small"
                      />
                    )}
                  </Box>
                </TableCell>

                <TableCell align="right">
                  <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                    {activeStrategy.status === 'running' && (
                      <Tooltip title="Pause Strategy">
                        <IconButton
                          size="small"
                          color="warning"
                          onClick={() => handlePause(activeStrategy.id)}
                        >
                          <PauseIcon />
                        </IconButton>
                      </Tooltip>
                    )}

                    {activeStrategy.status === 'paused' && (
                      <Tooltip title="Resume Strategy">
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => handleResume(activeStrategy.id)}
                        >
                          <PlayIcon />
                        </IconButton>
                      </Tooltip>
                    )}

                    {(activeStrategy.status === 'running' ||
                      activeStrategy.status === 'paused' ||
                      activeStrategy.status === 'error') && (
                      <Tooltip title="Stop Strategy">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleStop(activeStrategy.id)}
                        >
                          <StopIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
