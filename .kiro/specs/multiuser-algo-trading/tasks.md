# Implementation Plan

## Overview
This implementation plan breaks down the multi-user algorithmic trading platform into discrete, manageable coding tasks. Each task builds incrementally on previous tasks, with all code integrated into the system. Tasks are organized by functional area and include specific references to requirements.

**Current Status**: No implementation has started yet. This is a greenfield project.

**Testing Philosophy**: All tasks including tests are required for a comprehensive implementation. Unit and integration tests ensure code quality and reliability from the start. No tasks are marked as optional - all will be implemented.

## Implementation Approach

**Recommended Order**:
1. Start with infrastructure (Task 1) - sets up the foundation
2. Build authentication (Task 2) - enables user management
3. Implement market data engine (Task 4) - provides data for strategies
4. Create strategy execution engine (Task 5) - core trading logic
5. Build order management (Task 7) and position tracking (Task 8) - enables trading
6. Add remaining features incrementally based on priority

**Key Dependencies**:
- Tasks 3-17 depend on Task 1 (infrastructure)
- Tasks 5-8 depend on Task 4 (market data)
- Task 8 depends on Task 7 (orders before positions)
- Task 15 (frontend) can be built in parallel once backend APIs are defined

**Testing Approach**: All tasks including unit tests, integration tests, and end-to-end tests are required. This ensures a robust, production-ready system from the start.

## Task List

- [x] 1. Set up project structure and core infrastructure
  - Create directory structure for microservices (api_gateway, websocket_service, strategy_workers, order_processor, analytics_service, market_data_engine)
  - Set up Python virtual environment and install core dependencies (Flask, Flask-SocketIO, SQLAlchemy, Redis, psycopg2, pandas, numpy)
  - Create Docker base image with Python 3.11 and common dependencies
  - Set up configuration management for environment variables and secrets
  - Create database connection utilities with connection pooling (PgBouncer integration)
  - Create Redis connection utilities with cluster support
  - _Requirements: All requirements depend on this foundation_

- [x] 2. Implement authentication and user management
- [x] 2.1 Create user data models and database schema
  - Write SQLAlchemy models for User, UserAccount, AccountAccess, InvestorInvitation, Session tables
  - Create database migration scripts using Alembic
  - Implement password hashing utilities using bcrypt
  - Create user role enum (Admin, Trader, Investor)
  - _Requirements: 1.1, 1.4, 1.5_

- [x] 2.2 Implement authentication service
  - Write user registration endpoint with role assignment and password validation
  - Implement login endpoint with JWT token generation (PyJWT)
  - Create session validation middleware that checks token and inactivity timeout
  - Implement session refresh endpoint to update last_activity timestamp
  - Write logout endpoint to invalidate session tokens
  - Implement account locking logic after 3 failed login attempts
  - Create automatic unlock after 15 minutes
  - _Requirements: 1.1, 1.3, 1.4, 1.6_

- [x] 2.3 Implement user management service
  - Write endpoint to create user account for traders
  - Implement investor invitation system (create invitation with 7-day expiration)
  - Create invitation acceptance endpoint that creates AccountAccess record
  - Write endpoint to revoke investor access from account
  - Implement endpoint to get all users for an account
  - Create endpoint to get all accounts an investor can view
  - Write admin endpoint to update user roles
  - Implement admin endpoint to disable/enable user accounts
  - _Requirements: 1.2, 14.1, 14.3_

- [x] 2.4 Write unit tests for authentication
  - Test user registration with valid and invalid inputs
  - Test login with correct and incorrect credentials
  - Test account locking after failed attempts
  - Test session timeout after 30 minutes inactivity
  - Test JWT token validation and expiration
  - _Requirements: 1.1, 1.3, 1.4, 1.6_

- [x] 3. Implement broker connection management
- [x] 3.1 Create broker connector interface and base classes
  - Define IBrokerConnector abstract base class with all required methods
  - Create BrokerCredentials, BrokerOrder, BrokerOrderResponse data classes
  - Write broker credentials encryption utilities using AES-256
  - Create broker connection database models (BrokerConnection table)
  - _Requirements: 2.1, 2.4_

- [x] 3.2 Implement Angel One SmartAPI broker connector
  - Install SmartAPI Python SDK (smartapi-python)
  - Write Angel One connector class implementing IBrokerConnector
  - Implement connect() method with SmartAPI authentication (API key, client code, password, TOTP)
  - Write place_order() method to submit orders to Angel One (market, limit, stop-loss, stop-loss-market)
  - Implement get_order_status() and get_positions() methods
  - Create get_holdings() and get_funds() methods for account information
  - Write order update callback handler using WebSocket feed
  - Implement connection lost callback and reconnection logic (30s intervals, 10 attempts)
  - Add support for position conversion (INTRADAY to DELIVERY)
  - Implement support for multiple exchange segments (NSE, BSE, NFO, MCX)
  - Create mock broker connector for offline testing (simulates order fills without real broker)
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.3 Implement broker connection API endpoints
  - Write endpoint to connect broker account with encrypted credential storage
  - Create endpoint to disconnect broker and revoke credentials
  - Implement endpoint to get broker connection status
  - Write endpoint to list available broker plugins
  - _Requirements: 2.2, 2.4, 2.5_

- [x] 3.4 Write unit tests for broker connectors
  - Test broker connection with valid and invalid credentials
  - Test order placement and status retrieval
  - Test reconnection logic after connection loss
  - Test credential encryption and decryption
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 4. Implement market data engine
- [x] 4.1 Create market data models and storage
  - Write data classes for Tick, Candle, IndicatorValue
  - Create InfluxDB schema for storing completed candles
  - Implement Redis structures for forming candles (hash per symbol/timeframe)
  - Write candle buffer management (maintain last 500 candles in memory per timeframe)
  - _Requirements: 9.1, 9.4_

- [x] 4.2 Implement tick data processing and candle formation
  - Write tick data ingestion handler from NSE feed
  - Implement candle update logic for all timeframes (1m, 3m, 5m, 15m, 30m, 1h, 1d)
  - Create candle completion detection and event emission
  - Write logic to store completed candles in InfluxDB
  - Implement forming candle updates in Redis
  - _Requirements: 9.2, 9.3_

- [x] 4.3 Implement indicator calculation system
  - Create IIndicator interface for indicator plugins
  - Implement SMA indicator with configurable period
  - Implement EMA indicator with configurable period
  - Implement RSI indicator with configurable period
  - Implement MACD indicator with configurable parameters
  - Implement Bollinger Bands indicator
  - Write indicator calculation engine that manages indicator instances
  - Create indicator value caching in Redis
  - _Requirements: 9.3, 13.2_

- [x] 4.4 Implement market data subscription and distribution
  - Write subscription management (track which strategies need which symbols/timeframes)
  - Implement Angel One SmartAPI WebSocket feed connection for real-time market data
  - Create market data feed reconnection logic with immediate retry
  - Write Redis pub/sub for distributing market data updates across services
  - Implement WebSocket broadcasting of market data to clients
  - Add support for subscribing to multiple symbols and exchange segments (NSE, BSE, NFO, MCX)
  - Create market data source abstraction (live feed vs simulated feed)
  - _Requirements: 9.1, 9.5_

- [x] 4.6 Implement market data simulator for offline testing
  - Write historical data replay engine that streams past market data at configurable speed (1x, 2x, 5x, 10x)
  - Implement CSV file loader for custom tick data
  - Create realistic tick data generator with configurable volatility and trends
  - Write simulator control API (start, pause, resume, stop, set speed, jump to timestamp)
  - Implement simulator mode toggle in configuration (live/replay/simulated)
  - Add UI controls for simulator (play/pause, speed control, date/time picker)
  - Store simulated data in same format as live data for consistency
  - _Requirements: 9.1, 9.2, 11.1_

- [x] 4.5 Write unit tests for market data engine
  - Test candle formation from tick data for multiple timeframes
  - Test indicator calculations with sample data
  - Test candle completion events
  - Test market data feed reconnection
  - _Requirements: 9.2, 9.3, 9.5_

- [x] 5. Implement symbol mapping service
- [x] 5.1 Create symbol mapping data models and database schema
  - Write SQLAlchemy model for SymbolMapping table
  - Create database migration for symbol_mappings table with indexes
  - Implement SymbolMappingCache data class for in-memory caching
  - _Requirements: 13.1, 13.2_

- [x] 5.2 Implement symbol mapping service
  - Write method to load symbol mappings from CSV file
  - Implement getStandardSymbol() to convert broker symbol to standard symbol
  - Create getBrokerSymbol() to convert standard symbol to broker-specific format
  - Write validateSymbol() to check if symbol exists in mapping
  - Implement in-memory cache with Redis fallback for symbol lookups
  - Create admin endpoint to upload symbol mapping CSV files
  - _Requirements: 13.2, 13.3, 13.5_

- [x] 5.3 Create default symbol mappings for Angel One
  - Generate CSV file with common NSE symbols (NIFTY 50 stocks, BANKNIFTY, NIFTY)
  - Include broker tokens, exchange, instrument type, lot size, tick size
  - Load default mappings on first startup
  - _Requirements: 13.1, 13.4_

- [x] 5.4 Write unit tests for symbol mapping
  - Test symbol translation from standard to broker-specific format
  - Test reverse translation from broker to standard format
  - Test CSV file loading and validation
  - Test missing symbol error handling
  - _Requirements: 13.2, 13.6_

- [-] 6. Implement risk management service
- [x] 6.1 Create risk management data models and database schema
  - Write SQLAlchemy models for RiskLimits and StrategyLimits tables
  - Create database migrations for risk_limits and strategy_limits tables
  - Implement RiskLimits and LossCalculation data classes
  - _Requirements: 8.1, 12.1_

- [x] 6.2 Implement maximum loss limit tracking
  - Write setMaxLossLimit() endpoint to configure loss limit per account and trading mode
  - Implement calculateCurrentLoss() to sum realized and unrealized losses across all positions
  - Create checkLossLimit() that runs on every position update
  - Write pauseAllStrategies() to immediately stop all strategies when limit breached
  - Implement acknowledgeLimitBreach() endpoint for user to acknowledge and update limit
  - Create separate tracking for paper and live trading modes
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 6.3 Implement concurrent strategy limit management
  - Write admin endpoint to set global concurrent strategy limits per trading mode
  - Implement getActiveStrategyCount() to count running strategies per account
  - Create canActivateStrategy() validation check before strategy activation
  - Write enforceLimit() that rejects activation if limit reached
  - Display current count and limit on strategy activation UI
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 6.4 Write unit tests for risk management
  - Test loss limit calculation with multiple positions
  - Test automatic strategy pause when limit breached
  - Test concurrent strategy limit enforcement
  - Test separate limits for paper and live trading
  - _Requirements: 8.2, 8.3, 12.2_

- [x] 7. Implement strategy execution engine
- [x] 7.1 Create strategy interface and base classes
  - Define IStrategy abstract base class with initialize(), on_tick(), on_candle_complete(), cleanup() methods
  - Create StrategyConfig, TimeframeData, MultiTimeframeData, Signal data classes
  - Write strategy state management in Redis
  - Create strategy plugin manager for loading pre-built strategy modules only
  - _Requirements: 3.1, 3.2_

- [x] 7.2 Implement multi-timeframe data provider
  - Write service to aggregate data from multiple timeframes for a symbol
  - Implement logic to provide historical candles and forming candle for each timeframe
  - Create indicator value aggregation across timeframes
  - Write data synchronization to ensure consistent state during strategy evaluation
  - _Requirements: 9.3, 9.4_

- [x] 7.3 Implement strategy execution orchestrator
  - Write strategy loader that initializes pre-built strategies with configuration
  - Implement on_tick() execution when market data updates
  - Create on_candle_complete() execution when timeframe candles complete
  - Write signal validation logic before sending to order router
  - Implement strategy error handling (catch exceptions, log, pause strategy)
  - Create strategy pause/resume functionality
  - Integrate with concurrent strategy limit checks before activation
  - _Requirements: 3.2, 3.4, 3.5, 12.2_

- [x] 7.4 Implement pre-built strategy: Moving Average Crossover
  - Write MA Crossover strategy implementing IStrategy interface
  - Implement configurable fast and slow MA periods
  - Create entry signal logic (fast MA crosses above slow MA for long)
  - Write exit signal logic (fast MA crosses below slow MA)
  - Add support for multi-timeframe confirmation
  - _Requirements: 3.1, 3.3_

- [x] 7.5 Write unit tests for strategy execution
  - Test strategy loading and initialization
  - Test multi-timeframe data aggregation
  - Test signal generation from strategies
  - Test strategy error handling and isolation
  - _Requirements: 12.4, 12.5, 13.3_

- [x] 8. Implement order management and routing
- [x] 8.1 Create order and trade data models
  - Write SQLAlchemy models for Order and Trade tables
  - Create Order, Trade data classes with all required fields
  - Implement order status enum (pending, submitted, partial, filled, cancelled, rejected)
  - Write database indexes for efficient order queries
  - _Requirements: 10.4_

- [x] 8.2 Implement paper trading simulation
  - Write paper order execution simulator using current market prices
  - Implement market order fills at current price with configurable slippage (0.05%)
  - Create limit order fills when market reaches limit price
  - Write commission calculation (0.03% default)
  - Implement simulated position updates without broker communication
  - Create separate tracking for paper vs live orders
  - _Requirements: 3.4, 10.2, 10.3, 10.6_

- [x] 8.3 Implement order router for live trading with symbol mapping
  - Integrate symbol mapping service to translate standard symbols to broker-specific tokens before order submission
  - Write order submission to broker connectors based on account configuration
  - Implement order validation before submission
  - Create order status tracking and updates from broker callbacks
  - Translate broker symbols back to standard symbols in order responses
  - Write order rejection handling and user notification
  - Implement pending order timeout monitoring (30 seconds)
  - Create order audit trail with timestamps and trading mode indicator
  - _Requirements: 10.1, 10.3, 10.4, 10.5, 10.6, 13.2, 13.3_

- [x] 8.4 Create order management API endpoints
  - Write endpoint to submit order (validates trading mode and routes accordingly)
  - Implement endpoint to cancel pending order
  - Create endpoint to modify order parameters
  - Write endpoint to get order status and history
  - Implement endpoint to get all orders for account filtered by trading mode
  - _Requirements: 10.1, 10.2, 10.4_

- [x] 8.5 Write unit tests for order management
  - Test paper trading simulation with various order types
  - Test order routing to broker connectors with symbol mapping
  - Test order status tracking and updates
  - Test separation of paper and live trading orders
  - Test symbol translation in order flow
  - _Requirements: 10.2, 10.3, 10.6, 13.2_

- [ ] 9. Implement position management
- [ ] 9.1 Create position data models
  - Write SQLAlchemy model for Position table
  - Create Position, TrailingStopConfig data classes
  - Implement position side enum (long, short)
  - Write database indexes for position queries
  - _Requirements: 5.1_

- [x] 9.2 Implement position tracking and P&L calculation
  - Write openPosition() to create position from trade
  - Implement updatePosition() to modify position with new trades
  - Create closePosition() to finalize position
  - Write calculatePnL() for real-time unrealized P&L calculation
  - Implement separate position tracking for paper and live trading modes
  - Integrate with risk management service to trigger loss limit checks on every P&L update
  - _Requirements: 5.1, 5.2, 5.3, 8.2_

- [ ] 9.3 Implement trailing stop-loss management
  - Write trailing stop-loss initialization with configured percentage
  - Implement automatic stop price updates on favorable price movements
  - Create logic for long positions (stop = max(highestPrice * (1 - pct), currentStop))
  - Write logic for short positions (stop = min(lowestPrice * (1 + pct), currentStop))
  - Implement stop-loss trigger detection and exit order generation
  - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [ ] 9.4 Create position management API endpoints
  - Write endpoint to get all positions for account filtered by trading mode
  - Implement endpoint to get position history for date range
  - Create endpoint to manually close position
  - Write endpoint to update trailing stop-loss configuration
  - Implement endpoint to get real-time risk metrics (exposure, margin utilization)
  - _Requirements: 5.1, 5.3, 5.4, 5.5_

- [ ] 9.5 Write unit tests for position management
  - Test position P&L calculations with price updates
  - Test trailing stop-loss logic for long and short positions
  - Test position tracking separation for paper and live modes
  - Test integration with risk management loss limit checks
  - _Requirements: 4.2, 4.3, 5.2, 8.2_

- [x] 8.2 Implement position tracking and P&L calculation
  - Write position creation from trade execution
  - Implement position update logic when new trades occur
  - Create unrealized P&L calculation based on current market price
  - Write realized P&L calculation when position closes
  - Implement position closure logic
  - Create separate position tracking for paper vs live trading
  - _Requirements: 5.1, 5.4_

- [x] 8.3 Implement trailing stop-loss functionality
  - Write trailing stop-loss configuration per position
  - Implement stop price calculation for long positions (highestPrice * (1 - percentage))
  - Create stop price calculation for short positions (lowestPrice * (1 + percentage))
  - Write tick-by-tick stop price update logic
  - Implement automatic exit order submission when stop price is hit
  - Create trailing stop-loss trigger notification
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8.4 Create position management API endpoints
  - Write endpoint to get all positions for account filtered by trading mode
  - Implement endpoint to get position history
  - Create endpoint to manually close position
  - Write endpoint to update trailing stop-loss configuration
  - Implement endpoint to get real-time risk metrics (exposure, margin utilization)
  - _Requirements: 5.1, 5.2, 5.5_

- [x] 8.5 Write unit tests for position management
  - Test P&L calculations for long and short positions
  - Test trailing stop-loss logic with various price movements
  - Test position closure and realized P&L
  - _Requirements: 4.2, 4.3, 5.1_

- [x] 10. Implement backtesting engine
- [x] 10.1 Create backtest data models and configuration
  - Write BacktestConfig, BacktestResult, BacktestTrade, EquityPoint, PerformanceMetrics data classes
  - Create SQLAlchemy model for Backtest table
  - Implement backtest configuration validation
  - _Requirements: 11.2_

- [x] 10.2 Implement historical data loading
  - Write service to load historical candles from InfluxDB for date range
  - Implement multi-symbol data loading
  - Create multi-timeframe data synchronization
  - Write data validation to ensure completeness
  - _Requirements: 11.2_

- [x] 10.3 Implement backtest execution engine
  - Write chronological iteration through historical data
  - Implement strategy initialization with backtest config
  - Create tick-by-tick simulation with candle updates and indicator calculations
  - Write order fill simulation with configurable slippage and commission
  - Implement position tracking during backtest
  - Create equity curve calculation
  - _Requirements: 11.1, 11.4, 11.5_

- [x] 10.4 Implement performance metrics calculation
  - Write total return and annualized return calculations
  - Implement maximum drawdown calculation
  - Create Sharpe ratio and Sortino ratio calculations
  - Write win rate and profit factor calculations
  - Implement average win/loss calculations
  - Create trade statistics (consecutive wins/losses, holding time)
  - _Requirements: 11.3_

- [x] 10.5 Create backtest API endpoints
  - Write endpoint to start backtest with configuration
  - Implement endpoint to get backtest status and progress
  - Create endpoint to get backtest results with metrics and trades
  - Write endpoint to activate strategy in paper trading mode after successful backtest
  - Implement endpoint to list all backtests for a strategy
  - _Requirements: 11.1, 11.2, 11.3, 11.6_

- [x] 10.6 Write unit tests for backtesting
  - Test backtest execution with sample historical data
  - Test performance metrics calculations
  - Test order fill simulation with slippage and commission
  - _Requirements: 11.3, 11.4_

- [ ] 11. Implement analytics service
- [ ] 11.1 Create analytics data models
  - Write AnalyticsPeriod, StrategyPerformance, RiskMetrics, PerformanceSummary data classes
  - Create ProfitByTime, ProfitByDay, TradeStatistics data classes
  - _Requirements: 15.1_

- [ ] 11.2 Implement performance metrics calculation
  - Write service to calculate metrics for specified period and trading mode
  - Implement equity curve generation from trade history
  - Create strategy-level performance breakdown
  - Write risk metrics calculation (VaR, beta, correlation)
  - Implement drawdown analysis with recovery times
  - _Requirements: 15.2, 15.7_

- [ ] 11.3 Implement trade analysis
  - Write average holding time calculation
  - Implement best/worst trade identification
  - Create consecutive win/loss streak calculation
  - Write profit by time of day analysis
  - Implement profit by day of week analysis
  - _Requirements: 15.5_

- [ ] 11.4 Implement benchmark comparison
  - Write service to fetch NSE index data (NIFTY 50, BANK NIFTY)
  - Implement performance comparison calculations
  - Create relative performance metrics
  - _Requirements: 15.7_

- [ ] 11.5 Implement chart generation
  - Write equity curve chart data generation
  - Implement drawdown chart data generation
  - Create win/loss distribution histogram data
  - Write profit by time heatmap data
  - Implement strategy comparison bar chart data
  - _Requirements: 15.4_

- [ ] 11.6 Create analytics API endpoints
  - Write endpoint to get performance metrics for period and trading mode
  - Implement endpoint to get equity curve data
  - Create endpoint to get strategy breakdown by trading mode
  - Write endpoint to get detailed trade analysis
  - Implement endpoint to export reports in PDF and CSV formats
  - Create endpoint to compare performance against benchmark
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.6, 15.7_

- [ ] 11.7 Write unit tests for analytics
  - Test performance metrics calculations with sample trades
  - Test equity curve generation
  - Test benchmark comparison calculations
  - _Requirements: 15.2, 15.7_

- [ ] 12. Implement notification service
- [ ] 12.1 Create notification data models
  - Write SQLAlchemy model for Notification table
  - Create Notification, NotificationChannelConfig, NotificationPreferences data classes
  - Implement notification type and severity enums
  - _Requirements: 6.3_

- [ ] 11.2 Implement notification delivery system
  - Write in-app notification via WebSocket push (< 500ms latency)
  - Implement email notification via SMTP integration
  - Create SMS notification via Twilio integration
  - Write channel selection logic based on event severity
  - Implement notification batching to prevent spam
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 11.3 Implement notification triggers
  - Write order executed notification (paper and live modes)
  - Implement strategy error notification with error details
  - Create threshold alert notification for P&L limits
  - Write connection lost notification for broker and market data
  - Implement trailing stop triggered notification
  - Create investor invitation notification
  - Write session timeout warning notification (5 minutes before logout)
  - Implement account locked notification
  - _Requirements: 6.1, 6.2, 6.4, 6.5_

- [ ] 11.4 Create notification API endpoints
  - Write endpoint to get notification history for user
  - Implement endpoint to mark notifications as read
  - Create endpoint to configure notification preferences
  - Write endpoint to test notification delivery
  - _Requirements: 6.3, 6.5_

- [ ] 11.5 Write unit tests for notifications
  - Test notification delivery through different channels
  - Test notification trigger logic
  - Test notification preferences
  - _Requirements: 6.1, 6.3_

- [ ] 13. Implement WebSocket real-time updates
- [ ] 12.1 Create WebSocket service infrastructure
  - Set up Flask-SocketIO server with Redis adapter for multi-instance support
  - Implement WebSocket authentication using JWT tokens
  - Create room management for symbol/timeframe subscriptions
  - Write Redis pub/sub integration for broadcasting across instances
  - _Requirements: 5.2_

- [ ] 12.2 Implement market data WebSocket events
  - Write chart subscription handler (subscribe_chart event)
  - Implement initial historical data delivery
  - Create tick update broadcasting via Redis pub/sub
  - Write candle completion broadcasting
  - Implement indicator update broadcasting
  - _Requirements: 5.2, 9.2_

- [ ] 12.3 Implement trading activity WebSocket events
  - Write position update broadcasting
  - Implement order status update broadcasting
  - Create P&L update broadcasting (every 1 second)
  - Write strategy status update broadcasting
  - _Requirements: 5.1, 5.2_

- [ ] 12.4 Implement notification WebSocket events
  - Write in-app notification push
  - Implement notification read status updates
  - _Requirements: 6.1_

- [ ] 12.5 Write integration tests for WebSocket
  - Test WebSocket connection and authentication
  - Test market data subscription and updates
  - Test broadcasting across multiple instances
  - _Requirements: 5.2_

- [ ] 14. Implement admin dashboard and monitoring
- [ ] 13.1 Create admin data aggregation services
  - Write service to get active user count by role
  - Implement service to get total orders processed
  - Create service to get system resource utilization
  - Write service to get trading activity summary
  - _Requirements: 7.1_

- [ ] 13.2 Implement admin monitoring and alerts
  - Write CPU usage monitoring with alert when > 80% for 5 minutes
  - Implement memory usage monitoring
  - Create database connection pool monitoring
  - Write error rate monitoring by service
  - Implement custom metrics for trading activity (orders/sec, strategy errors)
  - _Requirements: 7.2_

- [ ] 13.3 Create admin API endpoints
  - Write endpoint to get system health dashboard data
  - Implement endpoint to get all user accounts with activity
  - Create endpoint to view trading activity for any account (read-only)
  - Write endpoint to disable/enable user accounts
  - Implement endpoint to view audit logs
  - Create endpoint to generate daily activity reports
  - _Requirements: 7.1, 7.3, 7.4, 7.5, 7.6_

- [ ] 13.4 Write unit tests for admin functionality
  - Test admin data aggregation
  - Test admin access control (cannot execute trades)
  - Test user account management
  - _Requirements: 7.4, 7.5_

- [ ] 15. Implement Google Cloud Run deployment
- [ ] 14.1 Create Docker containers for each service
  - Write Dockerfile for API Gateway service
  - Create Dockerfile for WebSocket service
  - Write Dockerfile for Strategy Execution service
  - Create Dockerfile for Order Processing service
  - Write Dockerfile for Analytics service
  - Implement multi-stage builds to minimize image size
  - _Requirements: All requirements depend on deployment_

- [ ] 14.2 Set up Cloud SQL and Cloud Memorystore
  - Create Cloud SQL PostgreSQL instance with high availability
  - Configure read replicas for analytics queries
  - Set up PgBouncer connection pooling
  - Create Cloud Memorystore Redis instance (5GB cluster)
  - Configure Redis cluster mode if needed
  - Write database initialization scripts
  - _Requirements: All requirements depend on database_

- [ ] 14.3 Configure Cloud Run services
  - Write cloud-run.yaml configuration for each service
  - Set up auto-scaling parameters (min instances, max instances, concurrency)
  - Configure resource limits (CPU, memory)
  - Implement sticky sessions for WebSocket service
  - Set up environment variables and secret references
  - _Requirements: All requirements depend on deployment_

- [ ] 14.4 Set up Google Secret Manager
  - Create secrets for database credentials
  - Store broker API keys in Secret Manager
  - Configure service account access to secrets
  - Implement automatic secret rotation policy (90 days)
  - _Requirements: 2.4_

- [ ] 14.5 Configure Cloud Load Balancer
  - Set up HTTPS load balancer with SSL certificate
  - Configure backend services for each Cloud Run service
  - Implement health checks
  - Set up URL routing rules
  - Configure sticky sessions for WebSocket connections
  - _Requirements: All requirements depend on load balancing_

- [ ] 14.6 Set up monitoring and logging
  - Configure Cloud Monitoring dashboards (system health, trading activity, user activity, errors)
  - Create custom metrics for trading-specific monitoring
  - Set up alerting policies (high error rate, high latency, high CPU, connection failures)
  - Implement structured JSON logging in all services
  - Configure log retention policies
  - _Requirements: 7.2_

- [ ] 14.7 Implement CI/CD pipeline
  - Create Cloud Build configuration for automated builds
  - Write build triggers for GitHub push events
  - Implement automated testing in build pipeline
  - Create Docker image build and push to Artifact Registry
  - Write deployment scripts for staging environment
  - Implement manual approval gate for production deployment
  - Create rolling update deployment strategy
  - _Requirements: All requirements depend on CI/CD_

- [ ] 14.8 Perform load testing and optimization
  - Run Artillery load tests for 500 concurrent users
  - Test WebSocket connection capacity (2500+ connections)
  - Measure API response times under load
  - Test auto-scaling behavior
  - Identify and optimize bottlenecks
  - Validate performance benchmarks
  - _Requirements: All requirements depend on performance_

- [ ] 16. Implement React frontend
- [ ] 16.1 Set up React project structure
  - Create React app with TypeScript
  - Set up routing with React Router
  - Configure state management with Redux or Context API
  - Install UI component library (Material-UI or Ant Design)
  - Set up WebSocket client with Socket.IO
  - Configure API client with Axios
  - _Requirements: All user-facing requirements_

- [ ] 16.2 Implement authentication UI
  - Create login page with email and password fields
  - Write registration page with role selection
  - Implement password validation UI
  - Create session timeout warning modal
  - Write account locked notification
  - Implement JWT token storage and refresh
  - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6_

- [ ] 16.3 Implement user dashboard
  - Create dashboard layout with navigation
  - Write portfolio summary component (equity, P&L, active strategies)
  - Implement separate views for paper and live trading
  - Create active positions table with real-time updates
  - Write active orders table with status updates
  - Implement strategy list with start/stop controls
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 16.4 Implement live charting component
  - Integrate TradingView Lightweight Charts library
  - Create chart component with symbol and timeframe selection
  - Implement WebSocket subscription for real-time updates
  - Write tick-by-tick candle update logic
  - Create indicator overlay controls
  - Implement position markers on chart
  - _Requirements: 5.2_

- [ ] 16.5 Implement strategy management UI
  - Create strategy library page showing available strategies
  - Write strategy configuration modal with parameter inputs
  - Implement trading mode selection (paper/live toggle)
  - Create strategy activation flow
  - Write strategy status monitoring component
  - Implement strategy pause/resume controls
  - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [ ] 16.6 Implement risk management UI
  - Create maximum loss limit configuration modal when activating first strategy
  - Write current loss display showing realized + unrealized losses
  - Implement loss limit breach notification modal with acknowledge button
  - Create loss limit update form
  - Write separate loss tracking displays for paper and live trading modes
  - Implement visual progress bar showing current loss vs limit
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 16.7 Implement concurrent strategy limit UI
  - Display current active strategy count and maximum limit on strategy activation page
  - Write error message when limit is reached
  - Create visual indicator showing available strategy slots
  - Implement admin control to set global limits
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 16.8 Implement symbol mapping admin UI
  - Create symbol mapping upload page for CSV files
  - Write symbol mapping table showing all mappings per broker
  - Implement validation feedback for uploaded mappings
  - Create missing symbol error notifications
  - _Requirements: 13.5, 13.6_

- [ ] 16.9 Implement backtesting UI
  - Create backtest configuration form (date range, capital, symbols, timeframes)
  - Write backtest execution progress indicator
  - Implement backtest results display with metrics
  - Create equity curve chart with Plotly.js
  - Write trade list table with details
  - Implement activate in paper trading button
  - _Requirements: 11.1, 11.2, 11.3, 11.6_

- [ ] 16.10 Implement analytics dashboard UI
  - Create performance metrics cards (return, Sharpe ratio, max drawdown, win rate)
  - Write equity curve chart component
  - Implement drawdown chart component
  - Create strategy breakdown comparison chart
  - Write trade analysis tables (best/worst trades, statistics)
  - Implement period selector (daily, weekly, monthly, yearly)
  - Create trading mode filter (paper/live)
  - Write export report button (PDF/CSV)
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

- [ ] 16.11 Implement broker connection UI
  - Create broker selection page
  - Write broker credential input form with encryption notice
  - Implement connection status indicator
  - Create disconnect broker button
  - Write connection error handling and display
  - _Requirements: 2.1, 2.2, 2.5_

- [ ] 16.12 Implement investor invitation UI
  - Create invite investor form for traders
  - Write pending invitations list
  - Implement revoke access button
  - Create investor account list showing all accessible accounts
  - Write investor view restrictions (read-only indicators)
  - _Requirements: 1.2, 14.1, 14.2, 14.3, 14.4_

- [ ] 16.13 Implement admin dashboard UI
  - Create system health overview with metrics
  - Write user management table with enable/disable controls
  - Implement trading activity summary charts
  - Create audit log viewer
  - Write daily report generation interface
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 16.14 Implement notification UI
  - Create notification bell icon with unread count
  - Write notification dropdown with recent notifications
  - Implement notification preferences modal
  - Create notification history page
  - Write mark as read functionality
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 16.15 Write end-to-end tests for critical user flows
  - Test user registration and login flow
  - Test strategy activation and execution flow
  - Test order submission and position tracking
  - Test backtest execution and results viewing
  - Test investor invitation and access
  - _Requirements: All user-facing requirements_

- [ ] 17. Implement offline testing and development tools

- [ ] 17.1 Create comprehensive testing environment
  - Write configuration profiles for different modes (live, paper, replay, simulated)
  - Implement environment variable management for switching between modes
  - Create Docker Compose setup for local development with all services
  - Write seed data scripts for test users, strategies, and historical data
  - Implement data export/import utilities for sharing test scenarios
  - _Requirements: All requirements_

- [ ] 17.2 Implement market replay system
  - Write historical data downloader from Angel One SmartAPI (download past 30 days on first run)
  - Create replay session manager (save/load replay state)
  - Implement time travel feature (jump to specific date/time in replay)
  - Write replay speed controls (0.5x to 100x speed)
  - Create replay event log showing all market events and strategy actions
  - Implement replay comparison tool (compare multiple strategy runs on same data)
  - _Requirements: 11.1, 11.2_

- [ ] 17.3 Create development mode features
  - Write strategy debugger with breakpoints on candle completion
  - Implement strategy variable inspector (view indicator values, signals in real-time)
  - Create order simulation with configurable fill delays and slippage
  - Write market condition simulator (trending, ranging, volatile, quiet)
  - Implement fast-forward mode (skip to next signal or interesting market event)
  - Create strategy performance comparison dashboard for replay sessions
  - _Requirements: 12.4, 12.5_

- [ ] 17.4 Build testing utilities and tools
  - Write CLI tool for running strategies in replay mode without UI
  - Create automated test suite runner for strategy validation
  - Implement performance profiler for strategy execution
  - Write data quality checker for historical data completeness
  - Create mock data generator for edge cases (gaps, circuit breakers, extreme volatility)
  - _Requirements: All requirements_

- [ ] 18. Integration and system testing
- [ ] 18.1 Implement end-to-end integration tests
  - Write test for complete trading flow (market data → strategy → order → position)
  - Test multi-timeframe strategy execution
  - Test paper trading vs live trading separation
  - Test broker connection and order routing
  - Test WebSocket real-time updates across services
  - _Requirements: All requirements_

- [ ] 18.2 Perform security testing
  - Test authentication and authorization for all endpoints
  - Verify role-based access control enforcement
  - Test account-level data isolation
  - Verify broker credential encryption
  - Test session timeout and account locking
  - _Requirements: 1.1, 1.4, 1.6, 2.4, 7.3_

- [ ] 18.3 Validate all requirements
  - Verify each requirement acceptance criteria is met
  - Test edge cases and error scenarios
  - Validate performance metrics (latency, throughput, capacity)
  - Test scalability with 500+ concurrent users
  - Verify all notifications are triggered correctly
  - _Requirements: All requirements_
