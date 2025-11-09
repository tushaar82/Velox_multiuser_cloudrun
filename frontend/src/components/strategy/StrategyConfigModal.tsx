import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  FormLabel,
  FormControlLabel,
  Switch,
  Box,
  Typography,
  Alert,
  Chip,
  Autocomplete,
  Slider,
} from '@mui/material';
import { MaxLossLimitModal } from '../risk';
import StrategyLimitIndicator from './StrategyLimitIndicator';
import { apiClient } from '../../services/api';
import type { Strategy, TradingMode, StrategyParameter } from '../../types';

interface StrategyConfigModalProps {
  open: boolean;
  strategy: Strategy | null;
  accountId: string;
  onClose: () => void;
  onActivate: (config: any) => void;
}

export default function StrategyConfigModal({
  open,
  strategy,
  accountId,
  onClose,
  onActivate,
}: StrategyConfigModalProps) {
  const [tradingMode, setTradingMode] = useState<TradingMode>('paper');
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showLossLimitModal, setShowLossLimitModal] = useState(false);
  const [hasLossLimit, setHasLossLimit] = useState(false);
  const [checkingLossLimit, setCheckingLossLimit] = useState(false);
  const [strategyLimit, setStrategyLimit] = useState<{
    maxConcurrentStrategies: number;
    currentActiveCount: number;
  } | null>(null);
  const [loadingLimit, setLoadingLimit] = useState(false);

  useEffect(() => {
    if (strategy) {
      // Initialize with default values
      const defaultParams: Record<string, any> = {};
      strategy.config.parameters.forEach((param) => {
        defaultParams[param.name] = param.default;
      });
      setParameters(defaultParams);
      setSelectedSymbols(strategy.config.symbols.slice(0, 1)); // Default to first symbol
      setSelectedTimeframes(strategy.config.timeframes);
    }
  }, [strategy]);

  useEffect(() => {
    if (open && accountId) {
      checkLossLimit();
      loadStrategyLimit();
    }
  }, [open, accountId, tradingMode]);

  const checkLossLimit = async () => {
    try {
      setCheckingLossLimit(true);
      const limits = await apiClient.getRiskLimits(accountId, tradingMode);
      setHasLossLimit(!!limits && limits.maxLossLimit > 0);
    } catch (err: any) {
      // 404 means no limit set yet
      if (err.response?.status === 404) {
        setHasLossLimit(false);
      }
    } finally {
      setCheckingLossLimit(false);
    }
  };

  const loadStrategyLimit = async () => {
    try {
      setLoadingLimit(true);
      const limits = await apiClient.getStrategyLimits(tradingMode);
      setStrategyLimit(limits);
    } catch (err: any) {
      console.error('Failed to load strategy limits:', err);
    } finally {
      setLoadingLimit(false);
    }
  };

  const validateParameters = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (selectedSymbols.length === 0) {
      newErrors.symbols = 'Please select at least one symbol';
    }

    if (selectedTimeframes.length === 0) {
      newErrors.timeframes = 'Please select at least one timeframe';
    }

    strategy?.config.parameters.forEach((param) => {
      const value = parameters[param.name];
      
      if (param.type === 'integer' || param.type === 'float') {
        if (param.min !== undefined && value < param.min) {
          newErrors[param.name] = `Value must be at least ${param.min}`;
        }
        if (param.max !== undefined && value > param.max) {
          newErrors[param.name] = `Value must be at most ${param.max}`;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleActivate = () => {
    if (!validateParameters()) {
      return;
    }

    // Check if strategy limit is reached
    if (strategyLimit && strategyLimit.currentActiveCount >= strategyLimit.maxConcurrentStrategies) {
      setErrors({
        general: `Strategy limit reached. You have ${strategyLimit.currentActiveCount} active strategies out of ${strategyLimit.maxConcurrentStrategies} allowed for ${tradingMode} trading mode. Please stop an existing strategy before activating a new one.`,
      });
      return;
    }

    // Check if loss limit is set before activating
    if (!hasLossLimit) {
      setShowLossLimitModal(true);
      return;
    }

    const config = {
      trading_mode: tradingMode,
      symbols: selectedSymbols,
      timeframes: selectedTimeframes,
      parameters,
    };

    onActivate(config);
  };

  const handleLossLimitSet = async (limit: number) => {
    try {
      await apiClient.setMaxLossLimit(accountId, tradingMode, limit);
      setShowLossLimitModal(false);
      setHasLossLimit(true);
      
      // Now proceed with strategy activation
      const config = {
        trading_mode: tradingMode,
        symbols: selectedSymbols,
        timeframes: selectedTimeframes,
        parameters,
      };
      onActivate(config);
    } catch (err: any) {
      setErrors({ general: err.response?.data?.message || 'Failed to set loss limit' });
    }
  };

  const renderParameterInput = (param: StrategyParameter) => {
    const value = parameters[param.name];
    const error = errors[param.name];

    switch (param.type) {
      case 'integer':
      case 'float':
        return (
          <Box key={param.name} sx={{ mb: 3 }}>
            <Typography variant="body2" gutterBottom>
              {param.description}
            </Typography>
            {param.min !== undefined && param.max !== undefined ? (
              <Box sx={{ px: 1 }}>
                <Slider
                  value={value}
                  onChange={(_, newValue) =>
                    setParameters({ ...parameters, [param.name]: newValue })
                  }
                  min={param.min}
                  max={param.max}
                  step={param.type === 'integer' ? 1 : 0.1}
                  marks
                  valueLabelDisplay="on"
                />
              </Box>
            ) : (
              <TextField
                fullWidth
                type="number"
                value={value}
                onChange={(e) =>
                  setParameters({
                    ...parameters,
                    [param.name]:
                      param.type === 'integer'
                        ? parseInt(e.target.value)
                        : parseFloat(e.target.value),
                  })
                }
                error={!!error}
                helperText={error}
                inputProps={{
                  min: param.min,
                  max: param.max,
                  step: param.type === 'integer' ? 1 : 0.1,
                }}
              />
            )}
          </Box>
        );

      case 'boolean':
        return (
          <FormControlLabel
            key={param.name}
            control={
              <Switch
                checked={value}
                onChange={(e) =>
                  setParameters({ ...parameters, [param.name]: e.target.checked })
                }
              />
            }
            label={param.description}
            sx={{ mb: 2 }}
          />
        );

      case 'string':
        return (
          <TextField
            key={param.name}
            fullWidth
            label={param.description}
            value={value}
            onChange={(e) =>
              setParameters({ ...parameters, [param.name]: e.target.value })
            }
            error={!!error}
            helperText={error}
            sx={{ mb: 2 }}
          />
        );

      default:
        return null;
    }
  };

  if (!strategy) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Configure Strategy: {strategy.name}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mt: 2 }}>
          {errors.general && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errors.general}
            </Alert>
          )}

          {/* Strategy Limit Indicator */}
          {strategyLimit && !loadingLimit && (
            <StrategyLimitIndicator
              currentCount={strategyLimit.currentActiveCount}
              maxLimit={strategyLimit.maxConcurrentStrategies}
              tradingMode={tradingMode}
            />
          )}

          {/* Trading Mode Selection */}
          <FormControl component="fieldset" sx={{ mb: 3 }}>
            <FormLabel component="legend">Trading Mode</FormLabel>
            <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
              <Chip
                label="Paper Trading"
                color={tradingMode === 'paper' ? 'primary' : 'default'}
                onClick={() => setTradingMode('paper')}
                sx={{ cursor: 'pointer' }}
              />
              <Chip
                label="Live Trading"
                color={tradingMode === 'live' ? 'error' : 'default'}
                onClick={() => setTradingMode('live')}
                sx={{ cursor: 'pointer' }}
              />
            </Box>
            {tradingMode === 'live' && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                Live trading will execute real orders with real capital. Ensure you have tested
                this strategy thoroughly in paper trading mode first.
              </Alert>
            )}
            {!hasLossLimit && !checkingLossLimit && (
              <Alert severity="info" sx={{ mt: 2 }}>
                You will be prompted to set a maximum loss limit before activating this strategy.
              </Alert>
            )}
          </FormControl>

          {/* Symbol Selection */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <Autocomplete
              multiple
              options={strategy.config.symbols}
              value={selectedSymbols}
              onChange={(_, newValue) => setSelectedSymbols(newValue)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Symbols"
                  error={!!errors.symbols}
                  helperText={errors.symbols || 'Select symbols to trade'}
                />
              )}
            />
          </FormControl>

          {/* Timeframe Selection */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <Autocomplete
              multiple
              options={strategy.config.timeframes}
              value={selectedTimeframes}
              onChange={(_, newValue) => setSelectedTimeframes(newValue)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Timeframes"
                  error={!!errors.timeframes}
                  helperText={errors.timeframes || 'Select timeframes for analysis'}
                />
              )}
            />
          </FormControl>

          {/* Strategy Parameters */}
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Strategy Parameters
          </Typography>
          {strategy.config.parameters.map((param) => renderParameterInput(param))}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleActivate} 
          variant="contained" 
          color="primary"
          disabled={
            checkingLossLimit ||
            loadingLimit ||
            (strategyLimit !== null &&
              strategyLimit.currentActiveCount >= strategyLimit.maxConcurrentStrategies)
          }
        >
          Activate Strategy
        </Button>
      </DialogActions>

      <MaxLossLimitModal
        open={showLossLimitModal}
        tradingMode={tradingMode}
        onClose={() => setShowLossLimitModal(false)}
        onSave={handleLossLimitSet}
      />
    </Dialog>
  );
}
