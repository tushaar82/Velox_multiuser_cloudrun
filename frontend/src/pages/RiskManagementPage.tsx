import { useState } from 'react';
import {
  Container,
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Alert,
} from '@mui/material';
import { RiskManagementPanel } from '../components/risk';
import type { TradingMode } from '../types';

export default function RiskManagementPage() {
  const [tradingMode, setTradingMode] = useState<TradingMode>('paper');
  
  // TODO: Get actual account ID from auth context/store
  const accountId = 'user-account-id';

  const handleTabChange = (_: React.SyntheticEvent, newValue: TradingMode) => {
    setTradingMode(newValue);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Risk Management
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Monitor and configure loss limits to protect your capital
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Loss limits are tracked separately for paper and live trading modes. Set conservative
        limits to automatically pause all strategies when losses reach the configured threshold.
      </Alert>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tradingMode}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="Paper Trading" value="paper" />
          <Tab label="Live Trading" value="live" />
        </Tabs>
      </Paper>

      <RiskManagementPanel
        accountId={accountId}
        tradingMode={tradingMode}
      />
    </Container>
  );
}
