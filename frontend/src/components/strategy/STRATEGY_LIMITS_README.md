# Concurrent Strategy Limit UI Implementation

## Overview

This implementation provides UI components for managing concurrent strategy limits in the multi-user algorithmic trading platform. It addresses Requirements 12.1, 12.2, 12.3, and 12.4 from the specification.

## Components

### 1. StrategyLimitIndicator

**Location**: `frontend/src/components/strategy/StrategyLimitIndicator.tsx`

**Purpose**: Displays the current active strategy count and maximum limit with a visual progress indicator.

**Features**:
- Visual progress bar showing strategy slot utilization
- Color-coded status (green: < 80%, yellow: 80-99%, red: 100%)
- Status icons (checkmark, warning, error)
- Real-time count display (e.g., "3 / 5 Active")
- Available slots indicator
- Utilization percentage
- Error alert when limit is reached
- Warning alert when approaching limit (≥ 80%)
- Separate display for paper and live trading modes

**Usage**:
```tsx
<StrategyLimitIndicator
  currentCount={3}
  maxLimit={5}
  tradingMode="paper"
/>
```

### 2. StrategyLimitAdminControl

**Location**: `frontend/src/components/strategy/StrategyLimitAdminControl.tsx`

**Purpose**: Admin interface for configuring global concurrent strategy limits.

**Features**:
- Side-by-side cards for paper and live trading limits
- Current limit display
- Current active strategy count
- Last updated timestamp
- Input validation (1-100 strategies)
- Save button with loading state
- Success/error notifications
- Informational note about limit application
- Real-time data loading and updates

**Usage**:
```tsx
<StrategyLimitAdminControl />
```

**Admin Access**: Only visible to users with `UserRole.ADMIN` role.

### 3. StrategyConfigModal (Enhanced)

**Location**: `frontend/src/components/strategy/StrategyConfigModal.tsx`

**Enhancements**:
- Integrated `StrategyLimitIndicator` at the top of the modal
- Automatic loading of strategy limits when modal opens
- Validation check before strategy activation
- Disable activation button when limit is reached
- Clear error message when limit prevents activation
- Real-time limit updates when switching trading modes

## Integration Points

### StrategyPage

**Location**: `frontend/src/pages/StrategyPage.tsx`

**Changes**:
- Added "Admin: Strategy Limits" tab (visible only to admins)
- Integrated `StrategyLimitAdminControl` component
- Tab index 4 for admin controls

### AdminPage

**Location**: `frontend/src/pages/AdminPage.tsx`

**Changes**:
- Added tabbed interface with "Strategy Limits" as first tab
- Integrated `StrategyLimitAdminControl` component
- Placeholder tabs for future admin features

## API Integration

### Endpoints Used

1. **GET /risk/strategy-limits/:tradingMode**
   - Fetches current strategy limits for a trading mode
   - Returns: `{ tradingMode, maxConcurrentStrategies, currentActiveCount, lastUpdated }`

2. **POST /risk/strategy-limits**
   - Updates strategy limits for a trading mode
   - Body: `{ trading_mode, max_concurrent_strategies }`
   - Admin only

### API Client Methods

```typescript
// Get strategy limits
await apiClient.getStrategyLimits(tradingMode);

// Set strategy limits (admin only)
await apiClient.setStrategyLimits(tradingMode, maxStrategies);
```

## User Experience Flow

### For Traders

1. **Strategy Activation**:
   - Open strategy configuration modal
   - See strategy limit indicator at the top
   - View current utilization (e.g., "3 / 5 Active - 60% utilized")
   - If limit reached:
     - See red error alert
     - Activation button is disabled
     - Clear message: "Strategy limit reached. Please stop an existing strategy..."
   - If approaching limit (≥ 80%):
     - See yellow warning alert
     - Can still activate
     - Message: "You are approaching the strategy limit..."

2. **Trading Mode Switch**:
   - When switching between paper and live modes
   - Limit indicator updates automatically
   - Shows separate limits for each mode

### For Admins

1. **Setting Limits**:
   - Navigate to Admin Dashboard → Strategy Limits tab
   - Or Strategy Management → Admin: Strategy Limits tab
   - View current limits for both paper and live trading
   - See current active strategy counts
   - Adjust limits (1-100 strategies)
   - Click "Save" button
   - Receive confirmation message

2. **Monitoring**:
   - View real-time active strategy counts
   - See last updated timestamp
   - Understand that changes apply to new activations only

## Validation Rules

### Strategy Limit Validation

- **Minimum**: 1 strategy
- **Maximum**: 100 strategies
- **Enforcement**: Checked before strategy activation
- **Scope**: Per user account, per trading mode

### Error Messages

1. **Limit Reached**:
   ```
   Strategy limit reached. You have X active strategies out of Y allowed 
   for [paper/live] trading mode. Please stop an existing strategy before 
   activating a new one.
   ```

2. **Approaching Limit**:
   ```
   You are approaching the strategy limit. Only X slot(s) remaining.
   ```

3. **Admin Validation**:
   ```
   Limit must be at least 1
   Limit cannot exceed 100
   ```

## Visual Design

### Color Scheme

- **Green** (< 80% utilization): Healthy, plenty of slots available
- **Yellow** (80-99% utilization): Warning, approaching limit
- **Red** (100% utilization): Error, limit reached

### Icons

- **CheckCircle**: Healthy status
- **Warning**: Approaching limit
- **Error**: Limit reached
- **Save**: Admin save action

### Layout

- Progress bar: 8px height, rounded corners
- Cards: Material-UI Card component with elevation
- Spacing: Consistent 2-3 unit spacing between elements
- Typography: Body2 for labels, Caption for secondary text

## Testing Considerations

### Manual Testing Scenarios

1. **Trader - Below Limit**:
   - Activate strategies until 70% utilization
   - Verify green indicator
   - Verify activation works

2. **Trader - Approaching Limit**:
   - Activate strategies until 80-99% utilization
   - Verify yellow warning appears
   - Verify activation still works

3. **Trader - At Limit**:
   - Activate strategies until 100% utilization
   - Verify red error appears
   - Verify activation button is disabled
   - Verify clear error message

4. **Trader - Mode Switch**:
   - Switch between paper and live modes
   - Verify limits update correctly
   - Verify separate counts for each mode

5. **Admin - Set Limits**:
   - Navigate to admin controls
   - Change paper trading limit
   - Verify save succeeds
   - Verify limit updates immediately
   - Repeat for live trading limit

6. **Admin - Validation**:
   - Try setting limit < 1 (should fail)
   - Try setting limit > 100 (should fail)
   - Verify error messages

### Edge Cases

1. **No Active Strategies**: Should show 0 / X with green indicator
2. **Exactly at Limit**: Should show red with disabled button
3. **Network Error**: Should show error message, allow retry
4. **Concurrent Updates**: Admin changes limit while trader is activating
5. **Role Check**: Non-admin users should not see admin controls

## Requirements Mapping

### Requirement 12.1
✅ Admin can configure global maximum concurrent strategy limit

**Implementation**: `StrategyLimitAdminControl` component with save functionality

### Requirement 12.2
✅ System rejects strategy activation when limit is reached

**Implementation**: Validation in `StrategyConfigModal.handleActivate()` with disabled button

### Requirement 12.3
✅ Display current number of active strategies and maximum allowed limit

**Implementation**: `StrategyLimitIndicator` component with real-time counts

### Requirement 12.4
✅ Separate limits for paper and live trading modes

**Implementation**: All components support `tradingMode` parameter, separate API calls

## Future Enhancements

1. **Per-User Limits**: Allow admins to set custom limits per user
2. **Historical Tracking**: Show limit utilization over time
3. **Notifications**: Alert admins when many users hit limits
4. **Auto-Scaling**: Suggest limit increases based on usage patterns
5. **Resource Monitoring**: Show system resource usage alongside limits
6. **Bulk Operations**: Allow admins to adjust multiple limits at once

## Dependencies

- Material-UI components (Box, Card, Typography, LinearProgress, Alert, etc.)
- React hooks (useState, useEffect)
- API client for backend communication
- Type definitions from `../../types`

## File Structure

```
frontend/src/components/strategy/
├── StrategyLimitIndicator.tsx       # Visual limit indicator
├── StrategyLimitAdminControl.tsx    # Admin configuration UI
├── StrategyConfigModal.tsx          # Enhanced with limit checks
├── index.ts                         # Exports
└── STRATEGY_LIMITS_README.md        # This file
```

## Conclusion

This implementation provides a comprehensive UI for managing concurrent strategy limits, ensuring system stability while providing clear feedback to users. The visual indicators and validation prevent users from exceeding limits, while admin controls allow flexible configuration based on system capacity.
