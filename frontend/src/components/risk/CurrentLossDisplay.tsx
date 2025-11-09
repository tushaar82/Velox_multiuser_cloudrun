import { Box, Typography, LinearProgress, Paper, Chip, IconButton, Tooltip } from '@mui/material';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import EditIcon from '@mui/icons-material/Edit';
import type { TradingMode, RiskLimits } from '../../types';

interface CurrentLossDisplayProps {
  riskLimits: RiskLimits;
  tradingMode: TradingMode;
  onEditLimit: () => void;
}

export default function CurrentLossDisplay({
  riskLimits,
  tradingMode,
  onEditLimit,
}: CurrentLossDisplayProps) {
  const { maxLossLimit, currentLoss, isBreached } = riskLimits;
  
  // Calculate percentage of limit used
  const lossPercentage = Math.min((Math.abs(currentLoss) / maxLossLimit) * 100, 100);
  
  // Determine color based on percentage
  const getColor = () => {
    if (isBreached || lossPercentage >= 100) return 'error';
    if (lossPercentage >= 80) return 'warning';
    if (lossPercentage >= 60) return 'info';
    return 'success';
  };

  const color = getColor();

  return (
    <Paper 
      elevation={2} 
      sx={{ 
        p: 2, 
        borderLeft: 4, 
        borderColor: `${color}.main`,
        bgcolor: isBreached ? 'error.50' : 'background.paper',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isBreached ? (
            <WarningAmberIcon color="error" />
          ) : (
            <TrendingDownIcon color={color} />
          )}
          <Typography variant="h6">
            Loss Tracking - {tradingMode === 'paper' ? 'Paper' : 'Live'}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {isBreached && (
            <Chip 
              label="LIMIT BREACHED" 
              color="error" 
              size="small" 
              sx={{ fontWeight: 'bold' }}
            />
          )}
          <Tooltip title="Edit loss limit">
            <IconButton size="small" onClick={onEditLimit}>
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Current Loss
          </Typography>
          <Typography 
            variant="body1" 
            fontWeight="bold" 
            color={currentLoss < 0 ? 'error.main' : 'text.primary'}
          >
            ₹{Math.abs(currentLoss).toLocaleString()}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Maximum Limit
          </Typography>
          <Typography variant="body1" fontWeight="bold">
            ₹{maxLossLimit.toLocaleString()}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Remaining Buffer
          </Typography>
          <Typography 
            variant="body1" 
            fontWeight="bold"
            color={lossPercentage >= 80 ? 'warning.main' : 'success.main'}
          >
            ₹{Math.max(0, maxLossLimit - Math.abs(currentLoss)).toLocaleString()}
          </Typography>
        </Box>

        <Box sx={{ position: 'relative' }}>
          <LinearProgress 
            variant="determinate" 
            value={lossPercentage} 
            color={color}
            sx={{ 
              height: 10, 
              borderRadius: 1,
              bgcolor: 'grey.200',
            }}
          />
          <Typography
            variant="caption"
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              fontWeight: 'bold',
              color: lossPercentage > 50 ? 'white' : 'text.primary',
            }}
          >
            {lossPercentage.toFixed(1)}%
          </Typography>
        </Box>
      </Box>

      {lossPercentage >= 80 && !isBreached && (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'warning.50', borderRadius: 1 }}>
          <Typography variant="caption" color="warning.dark">
            ⚠️ Warning: You have used {lossPercentage.toFixed(0)}% of your loss limit. 
            Consider reviewing your positions and strategy performance.
          </Typography>
        </Box>
      )}

      {isBreached && (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'error.50', borderRadius: 1 }}>
          <Typography variant="caption" color="error.dark" fontWeight="bold">
            🛑 All strategies have been paused. Acknowledge the breach to continue.
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
