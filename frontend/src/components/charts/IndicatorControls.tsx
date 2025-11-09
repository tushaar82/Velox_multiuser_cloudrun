import React, { useState } from 'react';
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Menu,
  MenuItem,
  TextField,
  Typography,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';

export interface IndicatorConfig {
  type: string;
  enabled: boolean;
  params: { [key: string]: number };
  color: string;
}

interface IndicatorControlsProps {
  indicators: IndicatorConfig[];
  onIndicatorChange: (indicators: IndicatorConfig[]) => void;
}

const AVAILABLE_INDICATORS = [
  {
    type: 'SMA',
    label: 'Simple Moving Average',
    params: [{ name: 'period', label: 'Period', default: 20, min: 1, max: 200 }],
    color: '#2196f3',
  },
  {
    type: 'EMA',
    label: 'Exponential Moving Average',
    params: [{ name: 'period', label: 'Period', default: 20, min: 1, max: 200 }],
    color: '#ff9800',
  },
  {
    type: 'RSI',
    label: 'Relative Strength Index',
    params: [{ name: 'period', label: 'Period', default: 14, min: 2, max: 100 }],
    color: '#9c27b0',
  },
  {
    type: 'MACD',
    label: 'MACD',
    params: [
      { name: 'fast', label: 'Fast Period', default: 12, min: 2, max: 100 },
      { name: 'slow', label: 'Slow Period', default: 26, min: 2, max: 100 },
      { name: 'signal', label: 'Signal Period', default: 9, min: 2, max: 100 },
    ],
    color: '#4caf50',
  },
  {
    type: 'BB',
    label: 'Bollinger Bands',
    params: [
      { name: 'period', label: 'Period', default: 20, min: 2, max: 100 },
      { name: 'stdDev', label: 'Std Dev', default: 2, min: 1, max: 5 },
    ],
    color: '#f44336',
  },
];

export const IndicatorControls: React.FC<IndicatorControlsProps> = ({
  indicators,
  onIndicatorChange,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleAddClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleAddIndicator = (indicatorType: string) => {
    const indicatorDef = AVAILABLE_INDICATORS.find((ind) => ind.type === indicatorType);
    if (!indicatorDef) return;

    const params: { [key: string]: number } = {};
    indicatorDef.params.forEach((param) => {
      params[param.name] = param.default;
    });

    const newIndicator: IndicatorConfig = {
      type: indicatorType,
      enabled: true,
      params,
      color: indicatorDef.color,
    };

    onIndicatorChange([...indicators, newIndicator]);
    handleClose();
  };

  const handleToggleIndicator = (index: number) => {
    const updated = [...indicators];
    updated[index].enabled = !updated[index].enabled;
    onIndicatorChange(updated);
  };

  const handleRemoveIndicator = (index: number) => {
    const updated = indicators.filter((_, i) => i !== index);
    onIndicatorChange(updated);
  };

  const handleParamChange = (index: number, paramName: string, value: number) => {
    const updated = [...indicators];
    updated[index].params[paramName] = value;
    onIndicatorChange(updated);
  };

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2">Indicators</Typography>
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={handleAddClick}
          variant="outlined"
        >
          Add Indicator
        </Button>
      </Box>

      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
        {AVAILABLE_INDICATORS.map((indicator) => (
          <MenuItem key={indicator.type} onClick={() => handleAddIndicator(indicator.type)}>
            {indicator.label}
          </MenuItem>
        ))}
      </Menu>

      {indicators.length > 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {indicators.map((indicator, index) => {
            const indicatorDef = AVAILABLE_INDICATORS.find((ind) => ind.type === indicator.type);
            if (!indicatorDef) return null;

            return (
              <Box
                key={`${indicator.type}-${index}`}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  p: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                }}
              >
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={indicator.enabled}
                      onChange={() => handleToggleIndicator(index)}
                      size="small"
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          bgcolor: indicator.color,
                        }}
                      />
                      <Typography variant="body2">{indicatorDef.label}</Typography>
                    </Box>
                  }
                />
                <Box sx={{ display: 'flex', gap: 1, ml: 'auto' }}>
                  {indicatorDef.params.map((param) => (
                    <TextField
                      key={param.name}
                      label={param.label}
                      type="number"
                      size="small"
                      value={indicator.params[param.name]}
                      onChange={(e) =>
                        handleParamChange(index, param.name, Number(e.target.value))
                      }
                      inputProps={{ min: param.min, max: param.max }}
                      sx={{ width: 100 }}
                    />
                  ))}
                  <Button
                    size="small"
                    color="error"
                    onClick={() => handleRemoveIndicator(index)}
                  >
                    Remove
                  </Button>
                </Box>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
};
