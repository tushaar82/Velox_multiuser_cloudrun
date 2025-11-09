# Risk Management UI Components

This directory contains React components for managing risk limits and loss tracking in the algorithmic trading platform.

## Components

### 1. MaxLossLimitModal
Modal dialog for setting or updating the maximum loss limit for a trading mode.

**Props:**
- `open: boolean` - Controls modal visibility
- `tradingMode: TradingMode` - Either 'paper' or 'live'
- `currentLimit?: number` - Existing limit (if updating)
- `onClose: () => void` - Callback when modal is closed
- `onSave: (limit: number) => void` - Callback when limit is saved

**Features:**
- Input validation (minimum ₹1,000)
- Different messaging for paper vs live trading
- Warning alerts for live trading mode
- Currency formatting with rupee symbol

**Usage:**
```tsx
<MaxLossLimitModal
  open={showModal}
  tradingMode="paper"
  currentLimit={50000}
  onClose={() => setShowModal(false)}
  onSave={(limit) => handleSaveLimit(limit)}
/>
```

### 2. LossLimitBreachModal
Modal displayed when the maximum loss limit is breached, requiring user acknowledgment.

**Props:**
- `open: boolean` - Controls modal visibility
- `tradingMode: TradingMode` - Either 'paper' or 'live'
- `currentLimit: number` - The breached limit amount
- `currentLoss: number` - Current total loss amount
- `onClose: () => void` - Callback when modal is closed
- `onAcknowledge: (newLimit?: number) => void` - Callback when breach is acknowledged

**Features:**
- Cannot be dismissed without acknowledgment
- Two options: accept current limit or increase limit
- Validation ensures new limit is higher than current loss
- Warning messages for live trading
- Visual display of limit vs current loss

**Usage:**
```tsx
<LossLimitBreachModal
  open={isBreached}
  tradingMode="live"
  currentLimit={50000}
  currentLoss={-52000}
  onClose={() => {}}
  onAcknowledge={(newLimit) => handleAcknowledge(newLimit)}
/>
```

### 3. CurrentLossDisplay
Displays current loss tracking with visual progress bar and status indicators.

**Props:**
- `riskLimits: RiskLimits` - Risk limits data including current loss and max limit
- `tradingMode: TradingMode` - Either 'paper' or 'live'
- `onEditLimit: () => void` - Callback to edit the loss limit

**Features:**
- Real-time loss tracking display
- Visual progress bar showing percentage of limit used
- Color-coded status (green → info → warning → error)
- Remaining buffer calculation
- Warning messages at 80% threshold
- Breach status indicator
- Edit button for updating limits

**Usage:**
```tsx
<CurrentLossDisplay
  riskLimits={riskLimits}
  tradingMode="paper"
  onEditLimit={() => setShowEditModal(true)}
/>
```

### 4. RiskManagementPanel
Container component that manages risk limit state and displays the current loss tracking.

**Props:**
- `accountId: string` - User account ID
- `tradingMode: TradingMode` - Either 'paper' or 'live'
- `onLimitUpdated?: () => void` - Optional callback when limits are updated

**Features:**
- Fetches risk limits from API
- Auto-refreshes every 5 seconds
- Handles loading and error states
- Automatically shows breach modal when limit is breached
- Manages all child modals (edit, breach)
- Displays appropriate messages when no limits are set

**Usage:**
```tsx
<RiskManagementPanel
  accountId={user.accountId}
  tradingMode="paper"
  onLimitUpdated={() => console.log('Limits updated')}
/>
```

## Integration Points

### Strategy Activation Flow
The `StrategyConfigModal` has been updated to check for loss limits before activating a strategy:

1. User configures strategy parameters
2. User clicks "Activate Strategy"
3. System checks if loss limit is set for the selected trading mode
4. If no limit exists, `MaxLossLimitModal` is shown
5. User sets limit, then strategy activation proceeds
6. If limit exists, strategy activates immediately

### Dashboard Integration
The `DashboardPage` displays the `RiskManagementPanel` alongside the portfolio summary:

- Side-by-side layout on desktop (2:1 ratio)
- Stacked layout on mobile
- Updates in real-time with dashboard data
- Switches between paper and live trading modes

### Standalone Page
The `RiskManagementPage` provides a dedicated view for managing risk limits:

- Tab interface for switching between paper and live trading
- Full-width display of risk management panel
- Informational alerts about separate tracking

## API Integration

All components use the `apiClient` service for backend communication:

- `getRiskLimits(accountId, tradingMode)` - Fetch current limits
- `setMaxLossLimit(accountId, tradingMode, limit)` - Set/update limit
- `acknowledgeLimitBreach(accountId, tradingMode, newLimit?)` - Acknowledge breach

## State Management

Risk limits are fetched directly from the API rather than stored in Redux because:
- Real-time accuracy is critical for risk management
- Limits can be breached by backend processes
- Polling ensures UI stays synchronized with backend state
- Reduces complexity of Redux state management

## Styling

All components use Material-UI (MUI) v7 with:
- Consistent color scheme (success → info → warning → error)
- Responsive layouts
- Accessibility-compliant components
- Theme-aware styling

## Requirements Addressed

This implementation addresses the following requirements from the spec:

- **8.1**: Maximum loss limit configuration when activating first strategy
- **8.2**: Real-time tracking of realized + unrealized losses
- **8.3**: Automatic strategy pause when limit is breached
- **8.4**: Urgent notification when limit is reached
- **8.5**: Acknowledgment flow before strategy reactivation
- **8.6**: Separate loss tracking for paper and live trading modes

## Future Enhancements

Potential improvements for future iterations:

1. Historical loss limit breach log
2. Configurable warning thresholds (e.g., alert at 70%, 80%, 90%)
3. Email/SMS notifications when approaching limit
4. Loss limit recommendations based on account size
5. Graphical loss trend over time
6. Per-strategy loss limits in addition to account-wide limits
