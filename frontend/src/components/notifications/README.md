# Notification UI Components

This directory contains the notification UI components for the multi-user algorithmic trading platform.

## Components

### NotificationBell
A notification bell icon with unread count badge that appears in the main app bar. Clicking it opens a dropdown with recent notifications.

**Features:**
- Badge showing unread notification count
- Opens NotificationDropdown on click
- Integrated into MainLayout header

**Usage:**
```tsx
import { NotificationBell } from '../components/notifications';

<NotificationBell />
```

### NotificationDropdown
A popover dropdown that displays the 5 most recent notifications with quick actions.

**Features:**
- Shows last 5 notifications
- Mark individual notifications as read
- Visual indicators for severity (error, warning, info)
- Unread notifications highlighted
- "View All Notifications" button to navigate to full history
- Relative timestamps (e.g., "2 minutes ago")

**Props:**
- `onClose: () => void` - Callback when dropdown is closed

### NotificationHistory
Full notification history page with filtering and management capabilities.

**Features:**
- Complete list of all notifications
- Filter by severity (error, warning, info)
- Filter by read/unread status
- Mark individual notifications as read
- Mark all notifications as read
- Detailed notification information with timestamps
- Access to notification preferences

**Location:** `/notifications` route

### NotificationPreferencesModal
Modal dialog for configuring notification preferences per event type.

**Features:**
- Configure notification channels (in-app, email, SMS) per event type
- Enable/disable notifications for specific events
- Event types include:
  - Order Executed
  - Strategy Error
  - Threshold Alert
  - Connection Lost
  - Trailing Stop Triggered
  - Investor Invitation
  - Session Timeout Warning
  - Account Locked
  - System Alert
- Saves preferences to backend

**Props:**
- `open: boolean` - Controls modal visibility
- `onClose: () => void` - Callback when modal is closed

## Integration

### Redux Store
The notification components integrate with the Redux store via `notificationSlice`:

**State:**
- `notifications: Notification[]` - Array of all notifications
- `unreadCount: number` - Count of unread notifications
- `loading: boolean` - Loading state
- `error: string | null` - Error message if any

**Actions:**
- `fetchNotifications(userId)` - Fetch all notifications for user
- `markNotificationRead(notificationId)` - Mark notification as read
- `addNotification(notification)` - Add new notification (for WebSocket updates)
- `clearNotifications()` - Clear all notifications

### API Integration
The components use the following API endpoints:

- `GET /notifications/{userId}` - Get all notifications
- `PUT /notifications/{notificationId}/read` - Mark notification as read
- `GET /notifications/{userId}/preferences` - Get notification preferences
- `PUT /notifications/{userId}/preferences` - Update notification preferences

## Notification Types

The system supports the following notification types:

1. **order_executed** - When orders are filled (paper and live modes)
2. **strategy_error** - When strategies encounter errors
3. **threshold_alert** - When P&L reaches configured thresholds
4. **connection_lost** - When broker or market data connection drops
5. **trailing_stop_triggered** - When trailing stop-loss executes
6. **investor_invitation** - Investor invitation notifications
7. **session_timeout_warning** - Warning before automatic logout (5 minutes)
8. **account_locked** - When account is locked due to failed login attempts
9. **system_alert** - Important system notifications

## Severity Levels

Notifications have three severity levels:
- **error** - Critical issues requiring immediate attention (red)
- **warning** - Important issues that need attention (orange)
- **info** - Informational messages (blue)

## Real-time Updates

The notification system supports real-time updates via WebSocket:
- New notifications are pushed to the client
- Unread count updates automatically
- Notifications appear in dropdown and history immediately

## Requirements Addressed

This implementation addresses the following requirements:

- **Requirement 6.1** - Notification delivery through multiple channels
- **Requirement 6.2** - Immediate notifications for critical events
- **Requirement 6.3** - User-configurable notification preferences
- **Requirement 6.4** - Threshold alerts for P&L limits
- **Requirement 6.5** - Notification history and management
- **Requirement 6.6** - Session timeout warnings

## Styling

All components use Material-UI (MUI) components and follow the application's theme:
- Consistent spacing and typography
- Responsive design for mobile and desktop
- Accessible color contrast for severity indicators
- Smooth animations and transitions

## Future Enhancements

Potential improvements for future iterations:
- Notification grouping by type or time
- Search functionality in notification history
- Notification sound effects
- Desktop notifications (browser API)
- Notification templates for custom messages
- Bulk actions (delete, archive)
