import { Box, Typography, LinearProgress, Alert, Chip } from '@mui/material';
import { CheckCircle, Warning, Error as ErrorIcon } from '@mui/icons-material';
import type { TradingMode } from '../../types';

interface StrategyLimitIndicatorProps {
  currentCount: number;
  maxLimit: number;
  tradingMode: TradingMode;
}

export default function StrategyLimitIndicator({
  currentCount,
  maxLimit,
  tradingMode,
}: StrategyLimitIndicatorProps) {
  const availableSlots = maxLimit - currentCount;
  const utilizationPercent = (currentCount / maxLimit) * 100;
  
  const getStatusColor = () => {
    if (currentCount >= maxLimit) return 'error';
    if (utilizationPercent >= 80) return 'warning';
    return 'success';
  };

  const getStatusIcon = () => {
    if (currentCount >= maxLimit) return <ErrorIcon fontSize="small" />;
    if (utilizationPercent >= 80) return <Warning fontSize="small" />;
    return <CheckCircle fontSize="small" />;
  };

  const statusColor = getStatusColor();

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Strategy Slots ({tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'})
        </Typography>
        <Chip
          icon={getStatusIcon()}
          label={`${currentCount} / ${maxLimit} Active`}
          color={statusColor}
          size="small"
        />
      </Box>

      <LinearProgress
        variant="determinate"
        value={Math.min(utilizationPercent, 100)}
        color={statusColor}
        sx={{ height: 8, borderRadius: 1, mb: 1 }}
      />

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          {availableSlots > 0
            ? `${availableSlots} slot${availableSlots !== 1 ? 's' : ''} available`
            : 'No slots available'}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {utilizationPercent.toFixed(0)}% utilized
        </Typography>
      </Box>

      {currentCount >= maxLimit && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Strategy limit reached.</strong> You have reached the maximum number of
            concurrent strategies ({maxLimit}) for {tradingMode} trading mode. Please stop an
            existing strategy before activating a new one.
          </Typography>
        </Alert>
      )}

      {utilizationPercent >= 80 && currentCount < maxLimit && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="body2">
            You are approaching the strategy limit. Only {availableSlots} slot
            {availableSlots !== 1 ? 's' : ''} remaining.
          </Typography>
        </Alert>
      )}
    </Box>
  );
}
