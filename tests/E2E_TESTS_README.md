# End-to-End Tests Documentation

## Overview

The end-to-end tests in `test_e2e_user_flows.py` validate complete user journeys through the multi-user algorithmic trading platform. These tests ensure that critical workflows function correctly from start to finish.

## Test Coverage

### 1. User Registration and Login Flow
- **TestUserRegistrationAndLoginFlow**
  - Trader registration and login
  - Investor registration and login  
  - Admin registration and login
  - Session validation and refresh
  - Logout functionality

### 2. Strategy Activation and Execution Flow
- **TestStrategyActivationAndExecutionFlow**
  - Strategy activation in paper trading mode
  - Strategy configuration validation
  - Account requirement verification

### 3. Order Submission and Position Tracking Flow
- **TestOrderSubmissionAndPositionTrackingFlow**
  - Complete paper trading order flow (buy and sell)
  - Order and position tracking
  - Separation of paper vs live trading orders
  - Limit order submission and cancellation
  - Order history retrieval

### 4. Backtest Execution Flow
- **TestBacktestExecutionFlow**
  - Backtest configuration and execution
  - Results storage and retrieval
  - Performance metrics viewing
  - Backtest status tracking

### 5. Investor Invitation Flow
- **TestInvestorInvitationFlow**
  - Complete invitation workflow (invite → accept → access)
  - Investor read-only access verification
  - Access revocation
  - Expired invitation handling
  - Multiple investors on same account
  - Trader with multiple accounts

### 6. Multi-User Account Sharing
- **TestMultiUserAccountSharing**
  - Multiple investors accessing same account
  - Trader managing multiple accounts
  - Account access permissions

## Running the Tests

### Prerequisites
- PostgreSQL database must be running and configured
- Environment variables must be set (see `.env.example`)
- All dependencies must be installed (`pip install -r requirements.txt`)

### Run All E2E Tests
```bash
python3 -m pytest tests/test_e2e_user_flows.py -v
```

### Run Specific Test Class
```bash
python3 -m pytest tests/test_e2e_user_flows.py::TestUserRegistrationAndLoginFlow -v
```

### Run Specific Test
```bash
python3 -m pytest tests/test_e2e_user_flows.py::TestUserRegistrationAndLoginFlow::test_trader_registration_and_login_flow -v
```

## Test Database

The tests use the actual PostgreSQL database configured in the environment. This ensures:
- UUID types work correctly
- All database constraints are enforced
- Real-world database behavior is tested

**Note**: Tests perform cleanup after execution to avoid polluting the database.

## Key Features Tested

1. **Authentication & Authorization**
   - User registration with role assignment
   - Login with JWT token generation
   - Session management and timeout
   - Account locking after failed attempts

2. **Multi-User Account Management**
   - Trader account creation
   - Investor invitation system
   - Access control and permissions
   - Account sharing between users

3. **Trading Operations**
   - Paper trading order submission
   - Position tracking
   - Order status updates
   - Separation of paper and live trading

4. **Strategy Management**
   - Strategy activation
   - Configuration validation
   - Backtest execution
   - Results viewing

5. **Data Integrity**
   - Symbol mapping integration
   - Order-position relationship
   - User-account relationships
   - Invitation lifecycle

## Test Design Principles

1. **Complete Workflows**: Each test validates an entire user journey, not just individual functions
2. **Real Dependencies**: Tests use actual services and database connections
3. **Data Cleanup**: Tests clean up after themselves to avoid side effects
4. **Realistic Scenarios**: Tests simulate real user behavior and edge cases
5. **Comprehensive Coverage**: Tests cover all critical user-facing requirements

## Troubleshooting

### Database Connection Issues
If tests fail with database connection errors:
1. Verify PostgreSQL is running
2. Check environment variables in `.env`
3. Ensure database exists and migrations are applied

### UUID Type Errors
If you see UUID-related errors:
- Ensure you're using PostgreSQL, not SQLite
- SQLite doesn't support native UUID types

### Import Errors
If tests fail to import modules:
- Verify all dependencies are installed
- Check Python path includes project root
- Ensure all required services are implemented

## Future Enhancements

Potential additions to the E2E test suite:
- Live trading order flow (requires broker sandbox)
- WebSocket real-time updates
- Risk management limit enforcement
- Analytics report generation
- Admin dashboard operations
- Notification delivery testing
