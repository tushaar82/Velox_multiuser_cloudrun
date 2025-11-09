import { useState, useEffect } from 'react';
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
} from '@mui/material';
import type { TradingMode } from '../../types';

interface MaxLossLimitModalProps {
  open: boolean;
  tradingMode: TradingMode;
  currentLimit?: number;
  onClose: () => void;
  onSave: (limit: number) => void;
}

export default function MaxLossLimitModal({
  open,
  tradingMode,
  currentLimit,
  onClose,
  onSave,
}: MaxLossLimitModalProps) {
  const [limit, setLimit] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (currentLimit !== undefined) {
      setLimit(currentLimit.toString());
    } else {
      setLimit('');
    }
  }, [currentLimit, open]);

  const validateLimit = (): boolean => {
    const numLimit = parseFloat(limit);
    
    if (isNaN(numLimit) || numLimit <= 0) {
      setError('Please enter a valid positive amount');
      return false;
    }

    if (numLimit < 1000) {
      setError('Minimum loss limit is ₹1,000');
      return false;
    }

    setError('');
    return true;
  };

  const handleSave = () => {
    if (!validateLimit()) {
      return;
    }

    onSave(parseFloat(limit));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Set Maximum Loss Limit - {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Alert severity="info" sx={{ mb: 3 }}>
            {currentLimit !== undefined
              ? 'Update your maximum loss limit. All active strategies will be paused if this limit is breached.'
              : 'Set a maximum loss limit before activating your first strategy. All strategies will be automatically paused if total losses reach this amount.'}
          </Alert>

          <Typography variant="body2" color="text.secondary" gutterBottom>
            This limit applies to the combined realized and unrealized losses across all strategies
            in {tradingMode === 'paper' ? 'paper' : 'live'} trading mode.
          </Typography>

          <TextField
            fullWidth
            label="Maximum Loss Limit"
            type="number"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            error={!!error}
            helperText={error || 'Enter the maximum loss amount in rupees'}
            InputProps={{
              startAdornment: <InputAdornment position="start">₹</InputAdornment>,
            }}
            sx={{ mt: 3 }}
            autoFocus
          />

          {tradingMode === 'live' && (
            <Alert severity="warning" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Live Trading Warning:</strong> This limit protects your real capital.
                Set it conservatively based on your risk tolerance.
              </Typography>
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          {currentLimit !== undefined ? 'Update Limit' : 'Set Limit'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
