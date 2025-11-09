import { useState } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  StrategyLibrary,
  StrategyConfigModal,
  ActiveStrategyMonitor,
  StrategyLimitAdminControl,
} from '../components/strategy';
import type { Strategy } from '../types';
import { UserRole } from '../types';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { activateStrategy } from '../store/slices/strategySlice';

export default function StrategyPage() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const [activeTab, setActiveTab] = useState(0);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  const handleSelectStrategy = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setConfigModalOpen(true);
  };

  const handleActivateStrategy = async (config: any) => {
    if (!user?.accountId || !selectedStrategy) return;

    try {
      await dispatch(
        activateStrategy({
          accountId: user.accountId,
          strategyId: selectedStrategy.id,
          config,
        })
      ).unwrap();

      setSnackbar({
        open: true,
        message: `Strategy "${selectedStrategy.name}" activated successfully in ${config.trading_mode} mode`,
        severity: 'success',
      });
      setConfigModalOpen(false);
      setSelectedStrategy(null);
      setActiveTab(1); // Switch to active strategies tab
    } catch (error: any) {
      setSnackbar({
        open: true,
        message: error || 'Failed to activate strategy',
        severity: 'error',
      });
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  if (!user?.accountId) {
    return (
      <Box>
        <Alert severity="error">
          Unable to load account information. Please log in again.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Strategy Management
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage your algorithmic trading strategies
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Strategy Library" />
          <Tab label="Active Strategies (All)" />
          <Tab label="Paper Trading" />
          <Tab label="Live Trading" />
          {user?.role === UserRole.ADMIN && <Tab label="Admin: Strategy Limits" />}
        </Tabs>

        <Box sx={{ p: 3 }}>
          {activeTab === 0 && (
            <StrategyLibrary onSelectStrategy={handleSelectStrategy} />
          )}

          {activeTab === 1 && (
            <ActiveStrategyMonitor accountId={user.accountId} />
          )}

          {activeTab === 2 && (
            <ActiveStrategyMonitor
              accountId={user.accountId}
              tradingMode="paper"
            />
          )}

          {activeTab === 3 && (
            <ActiveStrategyMonitor
              accountId={user.accountId}
              tradingMode="live"
            />
          )}

          {activeTab === 4 && user?.role === UserRole.ADMIN && (
            <StrategyLimitAdminControl />
          )}
        </Box>
      </Paper>

      <StrategyConfigModal
        open={configModalOpen}
        strategy={selectedStrategy}
        accountId={user.accountId}
        onClose={() => {
          setConfigModalOpen(false);
          setSelectedStrategy(null);
        }}
        onActivate={handleActivateStrategy}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
