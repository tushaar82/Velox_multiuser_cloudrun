# Algorithmic Trading Platform - Frontend

React TypeScript frontend for the multi-user algorithmic trading platform.

## Technology Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Material-UI (MUI)** for UI components
- **Redux Toolkit** for state management
- **React Router** for routing
- **Axios** for API calls
- **Socket.IO Client** for WebSocket connections
- **TradingView Lightweight Charts** for live charting
- **Plotly.js** for analytics charts

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── auth/           # Authentication components
│   ├── dashboard/      # Dashboard components
│   ├── charts/         # Chart components
│   ├── strategy/       # Strategy management components
│   ├── risk/           # Risk management components
│   ├── broker/         # Broker connection components
│   ├── analytics/      # Analytics components
│   ├── admin/          # Admin components
│   ├── notifications/  # Notification components
│   └── investor/       # Investor components
├── layouts/            # Layout components
├── pages/              # Page components
├── services/           # API and WebSocket services
├── store/              # Redux store and slices
├── types/              # TypeScript type definitions
└── utils/              # Utility functions
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Update .env with your API endpoints
```

### Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

- `VITE_API_BASE_URL`: Backend API URL (default: http://localhost:5000)
- `VITE_WS_BASE_URL`: WebSocket server URL (default: http://localhost:5001)

## Features

### Implemented (Subtask 16.1)

- ✅ React project structure with TypeScript
- ✅ React Router setup
- ✅ Redux Toolkit state management
- ✅ Material-UI component library
- ✅ WebSocket client with Socket.IO
- ✅ API client with Axios
- ✅ Main layout with navigation
- ✅ Authentication layout
- ✅ Placeholder pages for all routes

### To Be Implemented

- 🔲 Authentication UI (16.2)
- 🔲 User dashboard (16.3)
- 🔲 Live charting component (16.4)
- 🔲 Strategy management UI (16.5)
- 🔲 Risk management UI (16.6, 16.7)
- 🔲 Symbol mapping admin UI (16.8)
- 🔲 Backtesting UI (16.9)
- 🔲 Analytics dashboard UI (16.10)
- 🔲 Broker connection UI (16.11)
- 🔲 Investor invitation UI (16.12)
- 🔲 Admin dashboard UI (16.13)
- 🔲 Notification UI (16.14)
- 🔲 End-to-end tests (16.15)

## API Integration

The frontend communicates with the backend through:

1. **REST API** (`/src/services/api.ts`): All CRUD operations
2. **WebSocket** (`/src/services/websocket.ts`): Real-time updates for:
   - Market data (ticks, candles, indicators)
   - Trading activity (positions, orders, P&L)
   - Strategy status updates
   - Notifications

## State Management

Redux Toolkit is used for global state management with the following slices:

- `authSlice`: User authentication and session management
- `dashboardSlice`: Dashboard summary and trading mode
- `strategySlice`: Strategy library and active strategies
- `orderSlice`: Order management
- `positionSlice`: Position tracking
- `notificationSlice`: Notifications and alerts

## User Roles

The platform supports three user roles:

1. **Admin**: System management, user management, monitoring
2. **Trader**: Full trading capabilities, strategy management
3. **Investor**: Read-only access to assigned accounts

## Development Guidelines

- Use TypeScript for type safety
- Follow Material-UI design patterns
- Keep components small and focused
- Use Redux for global state, local state for component-specific data
- Handle errors gracefully with user-friendly messages
- Implement loading states for async operations
- Use WebSocket for real-time updates
- Optimize performance for large datasets (virtualization, pagination)

## Testing

```bash
# Run tests (to be implemented in 16.15)
npm test
```

## License

Proprietary - All rights reserved
