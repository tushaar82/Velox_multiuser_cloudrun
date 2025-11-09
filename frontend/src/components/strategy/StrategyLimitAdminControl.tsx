import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Grid,
  Divider,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import { apiClient } from '../../services/api';
import type { TradingMode } from '../../types';

interface StrategyLimitConfig {
  tradingMode: TradingMode;
  maxConcurrentStrategies: number;
  currentActiveCount: number;
  lastUpdated: string;
}

export default function StrategyLimitAdminControl() {
  const [paperLimit, setPaperLimit] = useState<StrategyLimitConfig | null>(null);
  const [liveLimit, setLiveLimit] = useState<StrategyLimitConfig | null>(null);
  const [paperInput, setPaperInput] = useState<number>(5);
  const [liveInput, setLiveInput] = useState<number>(5);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<TradingMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadLimits();
  }, []);

  const loadLimits = async () => {
    try {
      setLoading(true);
      setError(null);

      const [paperData, liveData] = await Promise.all([
        apiClient.getStrategyLimits('paper'),
        apiClient.getStrategyLimits('live'),
      ]);

      setPaperLimit(paperData);
      setLiveLimit(liveData);
      setPaperInput(paperData.maxConcurrentStrategies);
      setLiveInput(liveData.maxConcurrentStrategies);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load strategy limits');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (tradingMode: TradingMode) => {
    const newLimit = tradingMode === 'paper' ? paperInput : liveInput;

    if (newLimit < 1) {
      setError('Limit must be at least 1');
      return;
    }

    if (newLimit > 100) {
      setError('Limit cannot exceed 100');
      return;
    }

    try {
      setSaving(tradingMode);
      setError(null);
      setSuccess(null);

      await apiClient.setStrategyLimits(tradingMode, newLimit);
      
      // Reload limits to get updated data
      await loadLimits();
      
      setSuccess(
        `Successfully updated ${tradingMode} trading limit to ${newLimit} concurrent strategies`
      );
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to update strategy limit');
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Concurrent Strategy Limits
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Configure the maximum number of strategies that can run simultaneously per user for each
        trading mode. These limits help manage system resources and ensure platform stability.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Paper Trading Limit */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Paper Trading Mode
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Simulated trading without real capital
              </Typography>

              <Divider sx={{ mb: 2 }} />

              {paperLimit && (
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Current Limit:
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {paperLimit.maxConcurrentStrategies} strategies
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Currently Active:
                    </Typography>
                    <Typography variant="body2">
                      {paperLimit.currentActiveCount} strategies
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">
                      Last Updated:
                    </Typography>
                    <Typography variant="body2">
                      {new Date(paperLimit.lastUpdated).toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              )}

              <TextField
                fullWidth
                type="number"
                label="New Limit"
                value={paperInput}
                onChange={(e) => setPaperInput(parseInt(e.target.value) || 0)}
                slotProps={{
                  htmlInput: {
                    min: 1,
                    max: 100,
                  },
                }}
                helperText="Set the maximum concurrent strategies (1-100)"
                sx={{ mb: 2 }}
              />

              <Button
                fullWidth
                variant="contained"
                startIcon={saving === 'paper' ? <CircularProgress size={20} /> : <SaveIcon />}
                onClick={() => handleSave('paper')}
                disabled={saving !== null || paperInput === paperLimit?.maxConcurrentStrategies}
              >
                {saving === 'paper' ? 'Saving...' : 'Save Paper Trading Limit'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Live Trading Limit */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Live Trading Mode
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Real trading with actual capital
              </Typography>

              <Divider sx={{ mb: 2 }} />

              {liveLimit && (
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Current Limit:
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {liveLimit.maxConcurrentStrategies} strategies
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Currently Active:
                    </Typography>
                    <Typography variant="body2">
                      {liveLimit.currentActiveCount} strategies
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">
                      Last Updated:
                    </Typography>
                    <Typography variant="body2">
                      {new Date(liveLimit.lastUpdated).toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              )}

              <TextField
                fullWidth
                type="number"
                label="New Limit"
                value={liveInput}
                onChange={(e) => setLiveInput(parseInt(e.target.value) || 0)}
                slotProps={{
                  htmlInput: {
                    min: 1,
                    max: 100,
                  },
                }}
                helperText="Set the maximum concurrent strategies (1-100)"
                sx={{ mb: 2 }}
              />

              <Button
                fullWidth
                variant="contained"
                color="error"
                startIcon={saving === 'live' ? <CircularProgress size={20} /> : <SaveIcon />}
                onClick={() => handleSave('live')}
                disabled={saving !== null || liveInput === liveLimit?.maxConcurrentStrategies}
              >
                {saving === 'live' ? 'Saving...' : 'Save Live Trading Limit'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Alert severity="info" sx={{ mt: 3 }}>
        <Typography variant="body2">
          <strong>Note:</strong> Changing these limits will not affect currently running
          strategies. The new limits will apply when users attempt to activate new strategies.
        </Typography>
      </Alert>
    </Box>
  );
}
