# Investor Invitation UI Components

This directory contains components for managing investor invitations and access to trading accounts.

## Overview

The investor invitation system allows traders to invite investors to view their trading accounts in read-only mode. Investors can monitor trading activity, view strategies, orders, positions, and analytics, but cannot modify settings or execute trades.

## Components

### InviteInvestorForm
Form component for traders to invite investors by email.

**Props:**
- `accountId: string` - The trading account ID
- `onInviteSent: () => void` - Callback when invitation is successfully sent

**Features:**
- Email validation
- Loading states
- Success/error feedback
- Auto-clears form after successful invitation

### PendingInvitationsList
Displays a list of pending invitations with status and expiration information.

**Props:**
- `accountId: string` - The trading account ID
- `refreshTrigger: number` - Trigger to refresh the list

**Features:**
- Shows invitation status (pending, accepted, rejected, expired)
- Displays expiration dates with visual indicators
- Allows revoking pending invitations
- Auto-refresh capability

### AccountUsersList
Shows all users with access to the trading account.

**Props:**
- `accountId: string` - The trading account ID
- `currentUserId: string` - Current user's ID (to prevent self-removal)
- `refreshTrigger: number` - Trigger to refresh the list

**Features:**
- Displays user roles (Trader, Investor, Admin)
- Shows when access was granted
- Allows revoking investor access
- Confirmation dialog before revoking
- Prevents removing the current user

### InvestorAccountsList
For investors to view all trading accounts they have access to.

**Props:**
- `onAccountSelect?: (accountId: string) => void` - Optional callback when account is selected

**Features:**
- Card-based layout showing accessible accounts
- Account status indicators (Active/Inactive)
- Read-only access badge
- Navigation to account dashboard

### ReadOnlyIndicator
Visual indicator that the user has read-only access.

**Props:**
- `variant?: 'banner' | 'chip' | 'icon'` - Display style (default: 'banner')
- `message?: string` - Custom message (optional)

**Variants:**
- `banner` - Full-width alert banner (default)
- `chip` - Compact chip with icon
- `icon` - Small icon with tooltip

## Usage Examples

### Trader View (Invite Investors)
```tsx
import { InviteInvestorForm, PendingInvitationsList, AccountUsersList } from '../components/investor';

function TraderInvestorPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  
  return (
    <>
      <InviteInvestorForm 
        accountId={accountId}
        onInviteSent={() => setRefreshTrigger(prev => prev + 1)}
      />
      <PendingInvitationsList 
        accountId={accountId}
        refreshTrigger={refreshTrigger}
      />
      <AccountUsersList 
        accountId={accountId}
        currentUserId={userId}
        refreshTrigger={refreshTrigger}
      />
    </>
  );
}
```

### Investor View (View Accessible Accounts)
```tsx
import { InvestorAccountsList, ReadOnlyIndicator } from '../components/investor';

function InvestorDashboard() {
  return (
    <>
      <ReadOnlyIndicator />
      <InvestorAccountsList />
    </>
  );
}
```

### Using Read-Only Indicators
```tsx
import { ReadOnlyIndicator } from '../components/investor';
import { useReadOnlyAccess } from '../hooks/useReadOnlyAccess';

function StrategyPage() {
  const isReadOnly = useReadOnlyAccess();
  
  return (
    <>
      {isReadOnly && <ReadOnlyIndicator variant="banner" />}
      
      <Button 
        disabled={isReadOnly}
        onClick={handleActivateStrategy}
      >
        Activate Strategy
        {isReadOnly && <ReadOnlyIndicator variant="icon" />}
      </Button>
    </>
  );
}
```

## Hooks

### useReadOnlyAccess
Returns `true` if the current user is an investor (read-only access).

```tsx
const isReadOnly = useReadOnlyAccess();
```

### useCanTrade
Returns `true` if the current user can execute trades (Trader or Admin).

```tsx
const canTrade = useCanTrade();
```

### useIsAdmin
Returns `true` if the current user is an admin.

```tsx
const isAdmin = useIsAdmin();
```

## API Endpoints Used

- `POST /users/accounts/:accountId/invite` - Send investor invitation
- `GET /users/accounts/:accountId/users` - Get all users with access
- `GET /users/accounts/:accountId/invitations` - Get pending invitations
- `DELETE /users/accounts/:accountId/access/:userId` - Revoke investor access
- `DELETE /users/invitations/:invitationId` - Revoke pending invitation
- `GET /users/investor/accounts` - Get accounts accessible to investor
- `POST /users/invitations/:invitationId/accept` - Accept invitation

## Requirements Addressed

This implementation addresses the following requirements:

- **Requirement 1.2**: Multi-user account sharing with role-based access
- **Requirement 14.1**: Investor can view all accessible accounts
- **Requirement 14.2**: Real-time viewing of positions, orders, and P&L
- **Requirement 14.3**: Prevent investors from modifying strategies or executing trades
- **Requirement 14.4**: Read-only access to analytics and reports

## Security Considerations

1. **Role-Based Access Control**: All API endpoints validate user roles
2. **Account Isolation**: Users can only access accounts they're invited to
3. **Invitation Expiration**: Invitations expire after 7 days
4. **Revocation**: Traders can revoke investor access at any time
5. **Read-Only Enforcement**: UI disables modification actions for investors

## Future Enhancements

- Email notifications when invitations are sent/accepted
- Invitation templates with custom messages
- Bulk invitation management
- Activity logs for investor access
- Granular permission controls (e.g., hide specific strategies)
