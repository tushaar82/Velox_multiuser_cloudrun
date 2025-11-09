import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { apiClient } from '../../services/api';
import { Strategy, ActiveStrategy } from '../../types';

interface StrategyState {
  strategies: Strategy[];
  activeStrategies: ActiveStrategy[];
  selectedStrategy: Strategy | null;
  loading: boolean;
  error: string | null;
}

const initialState: StrategyState = {
  strategies: [],
  activeStrategies: [],
  selectedStrategy: null,
  loading: false,
  error: null,
};

export const fetchStrategies = createAsyncThunk(
  'strategy/fetchStrategies',
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.listStrategies();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch strategies');
    }
  }
);

export const fetchActiveStrategies = createAsyncThunk(
  'strategy/fetchActiveStrategies',
  async ({ accountId, tradingMode }: { accountId: string; tradingMode?: string }, { rejectWithValue }) => {
    try {
      const response = await apiClient.getActiveStrategies(accountId, tradingMode);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch active strategies');
    }
  }
);

export const activateStrategy = createAsyncThunk(
  'strategy/activateStrategy',
  async (
    { accountId, strategyId, config }: { accountId: string; strategyId: string; config: any },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.activateStrategy(accountId, strategyId, config);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to activate strategy');
    }
  }
);

export const pauseStrategy = createAsyncThunk(
  'strategy/pauseStrategy',
  async (activeStrategyId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.pauseStrategy(activeStrategyId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to pause strategy');
    }
  }
);

export const resumeStrategy = createAsyncThunk(
  'strategy/resumeStrategy',
  async (activeStrategyId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.resumeStrategy(activeStrategyId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to resume strategy');
    }
  }
);

export const stopStrategy = createAsyncThunk(
  'strategy/stopStrategy',
  async (activeStrategyId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.stopStrategy(activeStrategyId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to stop strategy');
    }
  }
);

const strategySlice = createSlice({
  name: 'strategy',
  initialState,
  reducers: {
    setSelectedStrategy: (state, action) => {
      state.selectedStrategy = action.payload;
    },
    updateActiveStrategy: (state, action) => {
      const index = state.activeStrategies.findIndex((s) => s.id === action.payload.id);
      if (index !== -1) {
        state.activeStrategies[index] = action.payload;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Strategies
      .addCase(fetchStrategies.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStrategies.fulfilled, (state, action) => {
        state.loading = false;
        state.strategies = action.payload;
      })
      .addCase(fetchStrategies.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Fetch Active Strategies
      .addCase(fetchActiveStrategies.fulfilled, (state, action) => {
        state.activeStrategies = action.payload;
      })
      // Activate Strategy
      .addCase(activateStrategy.fulfilled, (state, action) => {
        state.activeStrategies.push(action.payload);
      })
      // Pause Strategy
      .addCase(pauseStrategy.fulfilled, (state, action) => {
        const index = state.activeStrategies.findIndex((s) => s.id === action.payload.id);
        if (index !== -1) {
          state.activeStrategies[index] = action.payload;
        }
      })
      // Resume Strategy
      .addCase(resumeStrategy.fulfilled, (state, action) => {
        const index = state.activeStrategies.findIndex((s) => s.id === action.payload.id);
        if (index !== -1) {
          state.activeStrategies[index] = action.payload;
        }
      })
      // Stop Strategy
      .addCase(stopStrategy.fulfilled, (state, action) => {
        state.activeStrategies = state.activeStrategies.filter((s) => s.id !== action.payload.id);
      });
  },
});

export const { setSelectedStrategy, updateActiveStrategy } = strategySlice.actions;
export default strategySlice.reducer;
