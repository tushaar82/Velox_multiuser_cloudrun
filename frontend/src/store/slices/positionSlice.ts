import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { apiClient } from '../../services/api';
import type { Position } from '../../types';

interface PositionState {
  positions: Position[];
  loading: boolean;
  error: string | null;
}

const initialState: PositionState = {
  positions: [],
  loading: false,
  error: null,
};

export const fetchPositions = createAsyncThunk(
  'position/fetchPositions',
  async ({ accountId, tradingMode }: { accountId: string; tradingMode?: string }, { rejectWithValue }) => {
    try {
      const response = await apiClient.getPositions(accountId, tradingMode);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch positions');
    }
  }
);

export const closePosition = createAsyncThunk(
  'position/closePosition',
  async (positionId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.closePosition(positionId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to close position');
    }
  }
);

export const updateTrailingStopLoss = createAsyncThunk(
  'position/updateTrailingStopLoss',
  async ({ positionId, config }: { positionId: string; config: any }, { rejectWithValue }) => {
    try {
      const response = await apiClient.updateTrailingStopLoss(positionId, config);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update trailing stop loss');
    }
  }
);

const positionSlice = createSlice({
  name: 'position',
  initialState,
  reducers: {
    updatePosition: (state, action) => {
      const index = state.positions.findIndex((p) => p.id === action.payload.id);
      if (index !== -1) {
        state.positions[index] = action.payload;
      } else {
        state.positions.unshift(action.payload);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPositions.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPositions.fulfilled, (state, action) => {
        state.loading = false;
        state.positions = action.payload;
      })
      .addCase(fetchPositions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(closePosition.fulfilled, (state, action) => {
        const index = state.positions.findIndex((p) => p.id === action.payload.id);
        if (index !== -1) {
          state.positions[index] = action.payload;
        }
      })
      .addCase(updateTrailingStopLoss.fulfilled, (state, action) => {
        const index = state.positions.findIndex((p) => p.id === action.payload.id);
        if (index !== -1) {
          state.positions[index] = action.payload;
        }
      });
  },
});

export const { updatePosition } = positionSlice.actions;
export default positionSlice.reducer;
