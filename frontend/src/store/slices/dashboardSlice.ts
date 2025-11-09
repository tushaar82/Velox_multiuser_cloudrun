import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '../../services/api';
import type { DashboardSummary, TradingMode } from '../../types';

interface DashboardState {
  summary: DashboardSummary | null;
  tradingMode: TradingMode;
  loading: boolean;
  error: string | null;
}

const initialState: DashboardState = {
  summary: null,
  tradingMode: 'paper',
  loading: false,
  error: null,
};

export const fetchDashboardSummary = createAsyncThunk(
  'dashboard/fetchSummary',
  async ({ accountId, tradingMode }: { accountId: string; tradingMode: TradingMode }, { rejectWithValue }) => {
    try {
      // Fetch positions, orders, and strategies to build summary
      const [positions, orders, strategies] = await Promise.all([
        apiClient.getPositions(accountId, tradingMode),
        apiClient.getOrders(accountId, tradingMode),
        apiClient.getActiveStrategies(accountId, tradingMode),
      ]);

      const equity = positions.reduce((sum: number, pos: any) => sum + pos.currentPrice * pos.quantity, 0);
      const dailyPnl = positions.reduce((sum: number, pos: any) => sum + pos.unrealizedPnl, 0);
      const activeStrategies = strategies.filter((s: any) => s.status === 'running').length;
      const openPositions = positions.filter((p: any) => !p.closedAt).length;
      const todayOrders = orders.filter((o: any) => {
        const orderDate = new Date(o.createdAt).toDateString();
        const today = new Date().toDateString();
        return orderDate === today;
      }).length;

      return {
        equity,
        dailyPnl,
        activeStrategies,
        openPositions,
        todayOrders,
      };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch dashboard summary');
    }
  }
);

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    setTradingMode: (state, action: PayloadAction<TradingMode>) => {
      state.tradingMode = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardSummary.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardSummary.fulfilled, (state, action) => {
        state.loading = false;
        state.summary = action.payload;
      })
      .addCase(fetchDashboardSummary.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setTradingMode } = dashboardSlice.actions;
export default dashboardSlice.reducer;
