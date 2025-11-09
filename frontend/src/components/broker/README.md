# Broker Connection UI Components

This directory contains the UI components for managing broker connections in the multi-user algorithmic trading platform.

## Components

### BrokerConnectionCard
Displays information about an existing broker connection with the ability to disconnect.

**Features:**
- Shows broker name and connection status (Connected/Disconnected)
- Displays connection ID, last connected time, and creation date
- Provides disconnect button with loading state
- Visual status indicator using color-coded chips

**Props:**
- `connection`: BrokerConnection object
- `onDisconnect`: Callback function to handle disconnection
- `loading`: Optional loading state

### BrokerSelectionList
Displays available broker connectors that users can connect to.

**Features:**
- Fetches and displays list of available brokers from API
- Shows broker details including:
  - Name and description
  - Version information
  - Supported exchanges (NSE, BSE, NFO, MCX)
  - Supported order types (market, limit, stop, etc.)
- Loading and error states
- Grid layout for responsive design

**Props:**
- `onSelectBroker`: Callback function when user selects a broker to connect

### BrokerCredentialForm
Modal dialog for entering broker credentials securely.

**Features:**
- Dynamic form generation based on broker's required credentials
- Password field visibility toggle for sensitive fields
- AES-256 encryption security notice
- Form validation (all required fields must be filled)
- Error handling and display
- Loading state during connection attempt

**Props:**
- `open`: Boolean to control modal visibility
- `broker`: BrokerInfo object or null
- `onClose`: Callback to close the modal
- `onSubmit`: Async callback to handle credential submission

## BrokerPage Implementation

The `BrokerPage` component integrates all broker components and provides:

1. **My Connections Tab**: Lists all existing broker connections with ability to disconnect
2. **Add New Connection Tab**: Shows available brokers to connect
3. **Connection Management**: Handles the full flow of selecting a broker, entering credentials, and establishing connection
4. **Real-time Status**: Displays connection status and allows refreshing
5. **Error Handling**: Shows user-friendly error messages via snackbar notifications

## API Integration

The components use the following API methods from `apiClient`:

- `listBrokers()`: Get available broker connectors
- `getBrokerConnections(accountId)`: Get user's existing connections
- `connectBroker(accountId, brokerName, credentials)`: Establish new connection
- `disconnectBroker(connectionId)`: Remove existing connection

## Security

- All credentials are encrypted using AES-256 encryption before storage
- Password fields are masked by default with toggle visibility option
- Security notice is prominently displayed in the credential form
- Credentials are never stored in plain text

## Requirements Addressed

This implementation addresses the following requirements from the spec:

- **Requirement 2.1**: Support for multiple NSE brokers through dedicated connectors
- **Requirement 2.2**: Broker connection establishment and verification
- **Requirement 2.5**: Broker disconnection and credential removal

## Usage Example

```tsx
import { BrokerPage } from './pages/BrokerPage';

// The page is already integrated into the app routing
// Access via /broker route when authenticated
```

## Future Enhancements

- Real-time connection status monitoring via WebSocket
- Connection health checks and automatic reconnection
- Broker-specific configuration options
- Connection history and audit trail
- Multi-account broker connections
