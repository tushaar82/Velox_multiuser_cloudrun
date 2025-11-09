import { useEffect } from 'react';
import {
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  Alert,
} from '@mui/material';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { fetchDashboardSummary, setTradingMode } from '../store/slices/dashboardSlice';
import { fetchPositions } from '../store/slices/positionSlice';
import { fetchOrders } from '../store/slices/orderSlice';
import { fetchActiveStrategies } from '../store/slices/strategySlice';
import {
  PortfolioSummary,
  ActivePositionsTable,
  ActiveOrdersTable,
  StrategyList,
} from '../components/dashboard';
import { LiveChartWithIndicators } from '../components/charts';
import { RiskManagementPanel } from '../components/risk';
import type { TradingMode } from '../types';

export default function DashboardPage() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const { summary, tradingMode, loading: dashboardLoading, error } = useAppSelector(
    (state) => state.dashboard
  );
  const { positions, loading: positionsLoading } = useAppSelector((state) => state.position);
  const { orders, loading: ordersLoading } = useAppSelector((state) => state.order);
  const { activeStrategies, loading: strategiesLoading } = useAppSelector(
    (state) => state.strategy
  );

  const accountId = user?.accountId || '';

  useEffect(() => {
    if (accountId) {
      // Fetch all dashboard data
      dispatch(fetchDashboardSummary({ accountId, tradingMode }));
      dispatch(fetchPositions({ accountId, tradingMode }));
      dispatch(fetchOrders({ accountId, tradingMode }));
      dispatch(fetchActiveStrategies({ accountId, tradingMode }));
    }
  }, [dispatch, accountId, tradingMode]);

  // Set up real-time updates every 5 seconds
  useEffect(() => {
    if (!accountId) return;

    const interval = setInterval(() => {
      dispatch(fetchDashboardSummary({ accountId, tradingMode }));
      dispatch(fetchPositions({ accountId, tradingMode }));
      dispatch(fetchOrders({ accountId, tradingMode }));
      dispatch(fetchActiveStrategies({ accountId, tradingMode }));
    }, 5000);

    return () => clearInterval(interval);
  }, [dispatch, accountId, tradingMode]);

  const handleTradingModeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newMode: TradingMode | null
  ) => {
    if (newMode !== null) {
      dispatch(setTradingMode(newMode));
    }
  };

  // Show message if user doesn't have an account
  if (!accountId) {
    return (
      <Box>
        <Typography variant="h4" sx={{ mb: 3 }}>Dashboard</Typography>
        <Alert severity="info" sx={{ mb: 3 }}>
          Welcome! To start trading, you need to create a trading account first.
          Please go to the Investor page to create or access an account.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Dashboard</Typography>
        <ToggleButtonGroup
          value={tradingMode}
          exclusive
          onChange={handleTradingModeChange}
          size="small"
        >
          <ToggleButton value="paper">Paper Trading</ToggleButton>
          <ToggleButton value="live">Live Trading</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 3, mb: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        <Box sx={{ flex: 2 }}>
          <PortfolioSummary
            summary={summary}
            tradingMode={tradingMode}
            loading={dashboardLoading}
          />
        </Box>
        <Box sx={{ flex: 1 }}>
          <RiskManagementPanel
            accountId={accountId}
            tradingMode={tradingMode}
          />
        </Box>
      </Box>

      <Box sx={{ mb: 3 }}>
        <LiveChartWithIndicators accountId={accountId} positions={positions} />
      </Box>

      <StrategyList strategies={activeStrategies} loading={strategiesLoading} />

      <ActivePositionsTable positions={positions} loading={positionsLoading} />

      <ActiveOrdersTable orders={orders} loading={ordersLoading} />
    </Box>
  );
}
