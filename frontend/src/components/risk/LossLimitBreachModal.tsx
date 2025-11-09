import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  InputAdornment,
  FormControlLabel,
  Radio,
  RadioGroup,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import type { TradingMode } from '../../types';

interface LossLimitBreachModalProps {
  open: boolean;
  tradingMode: TradingMode;
  currentLimit: number;
  currentLoss: number;
  onClose: () => void;
  onAcknowledge: (newLimit?: number) => void;
}

export default function LossLimitBreachModal({
  open,
  tradingMode,
  currentLimit,
  currentLoss,
  onClose,
  onAcknowledge,
}: LossLimitBreachModalProps) {
  const [action, setAction] = useState<'accept' | 'increase'>('accept');
  const [newLimit, setNewLimit] = useState<string>('');
  const [error, setError] = useState<string>('');

  const validateNewLimit = (): boolean => {
    if (action === 'accept') {
      return true;
    }

    const numLimit = parseFloat(newLimit);
    
    if (isNaN(numLimit) || numLimit <= 0) {
      setError('Please enter a valid positive amount');
      return false;
    }

    if (numLimit <= currentLimit) {
      setError(`New limit must be greater than current limit of ₹${currentLimit.toLocaleString()}`);
      return false;
    }

    if (numLimit <= Math.abs(currentLoss)) {
      setError(`New limit must be greater than current loss of ₹${Math.abs(currentLoss).toLocaleString()}`);
      return false;
    }

    setError('');
    return true;
  };

  const handleAcknowledge = () => {
    if (!validateNewLimit()) {
      return;
    }

    if (action === 'increase') {
      onAcknowledge(parseFloat(newLimit));
    } else {
      onAcknowledge();
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="sm" 
      fullWidth
      disableEscapeKeyDown
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <WarningAmberIcon color="error" />
        Loss Limit Breached - {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            <Typography variant="body2" fontWeight="bold">
              All strategies have been automatically paused!
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Your total loss has reached or exceeded the configured maximum loss limit.
            </Typography>
          </Alert>

          <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Maximum Loss Limit
            </Typography>
            <Typography variant="h6" color="error">
              ₹{currentLimit.toLocaleString()}
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Current Total Loss
            </Typography>
            <Typography variant="h6" color="error">
              ₹{Math.abs(currentLoss).toLocaleString()}
            </Typography>
          </Box>

          <Typography variant="body2" gutterBottom fontWeight="bold">
            Choose an action to continue:
          </Typography>

          <RadioGroup
            value={action}
            onChange={(e) => setAction(e.target.value as 'accept' | 'increase')}
          >
            <FormControlLabel
              value="accept"
              control={<Radio />}
              label={
                <Box>
                  <Typography variant="body2">
                    Accept current limit and review strategies
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    You can manually resume strategies after reviewing your positions
                  </Typography>
                </Box>
              }
            />
            <FormControlLabel
              value="increase"
              control={<Radio />}
              label={
                <Box>
                  <Typography variant="body2">
                    Increase loss limit and resume trading
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Set a new higher limit to allow strategies to continue
                  </Typography>
                </Box>
              }
            />
          </RadioGroup>

          {action === 'increase' && (
            <Box sx={{ mt: 2, ml: 4 }}>
              <TextField
                fullWidth
                label="New Maximum Loss Limit"
                type="number"
                value={newLimit}
                onChange={(e) => setNewLimit(e.target.value)}
                error={!!error}
                helperText={error || `Must be greater than ₹${Math.abs(currentLoss).toLocaleString()}`}
                InputProps={{
                  startAdornment: <InputAdornment position="start">₹</InputAdornment>,
                }}
                autoFocus
              />
            </Box>
          )}

          {tradingMode === 'live' && (
            <Alert severity="warning" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Important:</strong> Review your positions and strategy performance before
                resuming live trading. Consider reducing position sizes or adjusting strategy parameters.
              </Typography>
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleAcknowledge} variant="contained" color="primary" fullWidth>
          Acknowledge and Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
