# Requirements Document

## Introduction

This document outlines the requirements for a multi-user algorithmic trading platform designed for the National Stock Exchange (NSE) of India. The system enables multiple users to execute automated trading strategies across different brokers with support for trailing stop-loss functionality and plug-and-play strategy architecture.

## Glossary

- **Trading Platform**: The complete algorithmic trading software system
- **User**: An individual trader who uses the Trading Platform to execute trades
- **Broker Connector**: A software module that interfaces with a specific broker's API
- **Strategy Module**: A self-contained trading algorithm that can be loaded and executed by the Trading Platform
- **Trailing Stop-Loss**: A dynamic stop-loss order that automatically adjusts based on favorable price movements
- **NSE**: National Stock Exchange of India
- **Order Manager**: The component responsible for order creation, modification, and tracking
- **Position Manager**: The component that tracks and manages open trading positions
- **Market Data Feed**: Real-time price and market information from NSE
- **Tick Data**: Individual price updates that occur in real-time during market hours
- **Forming Candle**: An incomplete candlestick that updates tick-by-tick until the timeframe period completes
- **Historical Data**: Completed candlestick data from past trading periods
- **Indicator**: A mathematical calculation based on price and volume data used for trading decisions
- **Multi-Timeframe Strategy**: A trading strategy that analyzes multiple timeframes simultaneously (e.g., 1-minute, 5-minute, and daily charts)
- **Symbol Mapping**: A translation table that converts standard NSE symbols to broker-specific symbol tokens and vice versa
- **Concurrent Strategy Limit**: The maximum number of Strategy Modules that can run simultaneously per User Account
- **Maximum Loss Limit**: A user-configured threshold in rupees that triggers automatic strategy pause when total losses reach this amount
- **Paper Trading**: Simulated trading using real-time market data without executing actual orders or risking real capital
- **Live Trading**: Actual trading where orders are executed through broker connections with real capital at risk
- **Trading Mode**: The operational state of a strategy (either Paper Trading or Live Trading)
- **Admin User**: A user with elevated privileges to manage the Trading Platform, monitor all users, and configure system settings
- **Trader User**: A user who creates and executes trading strategies on their own account
- **Investor User**: A user who can view trading activity and performance but cannot modify strategies or execute trades
- **User Account**: A collection of users (one Trader and multiple Investors) sharing access to the same trading portfolio

## Requirements

### Requirement 1

**User Story:** As a user, I want to register with specific role permissions (Admin, Trader, or Investor), so that I can access appropriate features based on my role.

#### Acceptance Criteria

1. WHEN a new user submits valid registration details with role selection, THE Trading Platform SHALL create a unique account with encrypted credentials and assigned role permissions
2. WHEN a Trader User creates a User Account, THE Trading Platform SHALL allow the Trader to invite multiple Investor Users to view that account
3. WHEN a user attempts to log in with valid credentials, THE Trading Platform SHALL authenticate the user and grant role-based access within 2 seconds
4. IF a user enters incorrect credentials three consecutive times, THEN THE Trading Platform SHALL lock the account for 15 minutes
5. THE Trading Platform SHALL enforce password requirements of minimum 8 characters with at least one uppercase letter, one number, and one special character
6. WHEN a user session is inactive for 30 minutes, THE Trading Platform SHALL automatically log out the user

### Requirement 2

**User Story:** As a trader, I want to connect my broker account to the platform, so that I can execute trades through my preferred broker.

#### Acceptance Criteria

1. THE Trading Platform SHALL support at least three major NSE brokers through dedicated Broker Connectors
2. WHEN a User provides valid broker API credentials, THE Trading Platform SHALL establish and verify the connection within 5 seconds
3. WHEN a Broker Connector loses connection, THE Trading Platform SHALL attempt reconnection every 30 seconds for up to 5 minutes
4. THE Trading Platform SHALL store broker credentials in encrypted format using AES-256 encryption
5. WHEN a User requests to disconnect a broker, THE Trading Platform SHALL revoke all active sessions and remove stored credentials

### Requirement 3

**User Story:** As a trader, I want to select from pre-built trading strategies and switch between paper and live trading modes, so that I can test strategies safely before risking real capital.

#### Acceptance Criteria

1. THE Trading Platform SHALL provide a library of pre-built Strategy Modules that Users can select and activate
2. WHEN a User selects a Strategy Module, THE Trading Platform SHALL load and validate the strategy configuration within 3 seconds
3. THE Trading Platform SHALL allow Users to configure strategy parameters through a graphical interface without requiring code modifications
4. WHEN a User activates a Strategy Module, THE Trading Platform SHALL require the User to select either Paper Trading or Live Trading mode before execution begins
5. THE Trading Platform SHALL enforce the Admin-configured concurrent strategy limit when Users attempt to activate Strategy Modules

### Requirement 4

**User Story:** As a trader, I want the system to automatically place trailing stop-loss orders on my positions, so that I can protect profits while allowing for upside potential.

#### Acceptance Criteria

1. WHEN a User enables trailing stop-loss for a position, THE Trading Platform SHALL calculate the initial stop-loss price based on the configured trailing percentage
2. WHILE a position moves favorably, THE Trading Platform SHALL update the Trailing Stop-Loss price automatically within 1 second of each price update
3. WHEN the market price reaches the Trailing Stop-Loss level, THE Order Manager SHALL submit a market exit order within 500 milliseconds
4. THE Trading Platform SHALL allow Users to configure trailing stop-loss percentage between 0.1% and 10% with 0.1% increments
5. WHEN a Trailing Stop-Loss order is triggered, THE Trading Platform SHALL notify the User through the configured notification channel within 2 seconds

### Requirement 5

**User Story:** As a Trader User, I want to monitor my active positions and orders in real-time with clear indication of trading mode, so that I can track my trading performance and distinguish between paper and live trades.

#### Acceptance Criteria

1. THE Trading Platform SHALL display all active positions with current profit/loss updated every 1 second and Trading Mode indicator (Paper or Live)
2. WHEN an order status changes, THE Trading Platform SHALL update the order display within 500 milliseconds
3. THE Trading Platform SHALL provide separate dashboards for Paper Trading and Live Trading showing portfolio value, daily profit/loss, and active strategy count
4. WHEN a Trader User or Investor User requests position history, THE Trading Platform SHALL retrieve and display records for the selected date range and Trading Mode within 3 seconds
5. THE Trading Platform SHALL calculate and display real-time risk metrics including total exposure and margin utilization separately for Paper Trading and Live Trading portfolios

### Requirement 15

**User Story:** As a Trader User or Investor User, I want comprehensive analytics and performance metrics, so that I can evaluate trading effectiveness and make data-driven decisions.

#### Acceptance Criteria

1. THE Trading Platform SHALL provide an analytics dashboard with daily, weekly, monthly, and yearly performance views
2. THE Trading Platform SHALL calculate and display advanced metrics including Sharpe ratio, Sortino ratio, maximum drawdown, average win/loss ratio, and profit factor
3. WHEN a user requests strategy-level analytics, THE Trading Platform SHALL display performance breakdown by individual Strategy Module
4. THE Trading Platform SHALL generate visual charts including equity curve, drawdown chart, win/loss distribution, and profit by time of day
5. THE Trading Platform SHALL provide trade analysis showing average holding time, best and worst trades, and consecutive win/loss streaks
6. WHEN a user exports analytics, THE Trading Platform SHALL generate downloadable reports in PDF and CSV formats within 5 seconds
7. THE Trading Platform SHALL calculate risk-adjusted returns and compare performance against NSE benchmark indices

### Requirement 6

**User Story:** As a trader, I want to receive notifications about important trading events, so that I can stay informed about my automated trading activities.

#### Acceptance Criteria

1. WHEN an order is executed, THE Trading Platform SHALL send a notification to the User within 2 seconds
2. WHEN a Strategy Module generates an error, THE Trading Platform SHALL notify the User immediately with error details
3. THE Trading Platform SHALL support notification delivery through email, SMS, and in-app channels
4. WHEN a position reaches a profit or loss threshold configured by the User, THE Trading Platform SHALL trigger an alert notification
5. THE Trading Platform SHALL allow Users to configure notification preferences for each event type independently

### Requirement 7

**User Story:** As an Admin User, I want to manage all user accounts and monitor system health, so that I can ensure platform stability, security, and proper access control.

#### Acceptance Criteria

1. THE Trading Platform SHALL provide an admin dashboard displaying active user count by role, total orders processed, and system resource utilization
2. WHEN system CPU usage exceeds 80% for more than 5 minutes, THE Trading Platform SHALL alert Admin Users
3. THE Trading Platform SHALL log all user authentication attempts with timestamp, IP address, and role information
4. WHEN an Admin User disables a user account, THE Trading Platform SHALL immediately terminate all active sessions for that user and associated Investor Users
5. THE Trading Platform SHALL allow Admin Users to view trading activity and performance metrics for all User Accounts
6. THE Trading Platform SHALL generate daily reports of trading activity including order count by user role, execution rate, and error frequency

### Requirement 14

**User Story:** As an Investor User, I want to view real-time and historical performance of the trading account I'm invited to, so that I can monitor my investment without interfering with trading operations.

#### Acceptance Criteria

1. WHEN an Investor User logs in, THE Trading Platform SHALL display all User Accounts to which the Investor has been granted access
2. THE Trading Platform SHALL allow Investor Users to view real-time positions, orders, and profit/loss for their assigned User Accounts
3. THE Trading Platform SHALL prevent Investor Users from modifying strategies, executing trades, or changing Trading Mode settings
4. WHEN an Investor User requests analytics, THE Trading Platform SHALL provide read-only access to all performance reports and charts
5. THE Trading Platform SHALL send notifications to Investor Users for significant events (large losses, strategy errors) on their assigned User Accounts

### Requirement 8

**User Story:** As a trader, I want to set a maximum loss limit in rupees for all my strategies combined, so that I can control my total risk exposure.

#### Acceptance Criteria

1. WHEN a Trader User activates any Strategy Module, THE Trading Platform SHALL require the User to configure a maximum loss limit in rupees
2. THE Trading Platform SHALL track cumulative realized and unrealized losses across all active Strategy Modules for each User Account
3. WHEN the total loss across all strategies reaches the configured maximum loss limit, THE Trading Platform SHALL immediately pause all active Strategy Modules for that User Account
4. THE Trading Platform SHALL send an urgent notification to the User within 2 seconds when the maximum loss limit is reached
5. THE Trading Platform SHALL prevent strategy reactivation until the User acknowledges the loss limit breach and updates the limit or accepts the current limit
6. THE Trading Platform SHALL calculate losses separately for Paper Trading and Live Trading modes with independent maximum loss limits

### Requirement 11

**User Story:** As a trader, I want to backtest pre-built strategies against historical data, so that I can evaluate performance before moving to paper or live trading.

#### Acceptance Criteria

1. THE Trading Platform SHALL provide a backtesting engine that executes pre-built Strategy Modules against historical NSE market data
2. WHEN a User initiates a backtest, THE Trading Platform SHALL allow selection of date range, initial capital, instruments, and timeframes to test
3. WHEN a backtest completes, THE Trading Platform SHALL generate a performance report including total return, maximum drawdown, Sharpe ratio, win rate, and trade-by-trade details
4. THE Trading Platform SHALL simulate order execution with configurable slippage and commission parameters during backtesting
5. THE Trading Platform SHALL complete backtests for Multi-Timeframe Strategies with up to 1 year of intraday data within 60 seconds
6. WHEN a User is satisfied with backtest results, THE Trading Platform SHALL allow direct activation of the strategy in Paper Trading mode

### Requirement 12

**User Story:** As an Admin User, I want to control how many strategies can run simultaneously per user, so that I can manage system resources and prevent overload.

#### Acceptance Criteria

1. THE Trading Platform SHALL allow Admin Users to configure a global maximum concurrent strategy limit that applies to all Trader Users
2. WHEN a Trader User attempts to activate a Strategy Module that would exceed the concurrent strategy limit, THE Trading Platform SHALL reject the activation and display the current limit
3. THE Trading Platform SHALL display the current number of active strategies and the maximum allowed limit on the strategy activation interface
4. WHEN an Admin User modifies the concurrent strategy limit, THE Trading Platform SHALL apply the new limit immediately without affecting currently running strategies
5. THE Trading Platform SHALL count active strategies separately for Paper Trading and Live Trading modes with independent limits for each mode

### Requirement 9

**User Story:** As a trader, I want the system to handle market data efficiently with tick-by-tick updates, so that my strategies receive timely price updates and indicators recalculate in real-time.

#### Acceptance Criteria

1. THE Trading Platform SHALL subscribe to NSE Market Data Feed for instruments configured in active Strategy Modules
2. WHEN new Tick Data arrives, THE Trading Platform SHALL update the Forming Candle for all relevant timeframes within 50 milliseconds
3. WHEN a Forming Candle updates, THE Trading Platform SHALL recalculate all Indicators that depend on that timeframe within 100 milliseconds
4. THE Trading Platform SHALL maintain Historical Data for each subscribed instrument with at least 500 completed candles per timeframe
5. WHEN Market Data Feed connection is lost, THE Trading Platform SHALL pause all active Strategy Modules and attempt reconnection

### Requirement 13

**User Story:** As a trader, I want the platform to handle different broker symbol formats automatically, so that I can switch brokers without worrying about symbol compatibility.

#### Acceptance Criteria

1. THE Trading Platform SHALL maintain a symbol mapping table that translates standard NSE symbols to broker-specific symbol tokens
2. WHEN a Strategy Module generates a trade signal with a standard symbol, THE Trading Platform SHALL automatically convert it to the appropriate broker-specific symbol token before order submission
3. WHEN Market Data Feed provides updates with broker-specific symbols, THE Trading Platform SHALL convert them to standard symbols for Strategy Module consumption
4. THE Trading Platform SHALL support symbol mapping for at least three major brokers with different symbol formats
5. WHEN an Admin User adds a new broker, THE Trading Platform SHALL allow upload of symbol mapping configuration in CSV format
6. WHEN a symbol mapping is missing for a requested instrument, THE Trading Platform SHALL log an error and notify the Admin User within 5 seconds

### Requirement 10

**User Story:** As a trader, I want my orders to be executed reliably across different brokers or simulated in paper trading, so that I can trust the platform to handle my trades correctly.

#### Acceptance Criteria

1. WHEN a Strategy Module in Live Trading mode generates a trade signal, THE Order Manager SHALL create and submit an order to the connected Broker Connector within 200 milliseconds
2. WHEN a Strategy Module in Paper Trading mode generates a trade signal, THE Order Manager SHALL simulate order execution using current market prices without sending orders to the broker
3. WHEN a Broker Connector returns an order rejection, THE Order Manager SHALL log the rejection reason and notify the User within 1 second
4. THE Order Manager SHALL track order status transitions from submission through completion or cancellation for both Paper Trading and Live Trading modes
5. WHEN an order in Live Trading mode remains in pending state for more than 30 seconds, THE Order Manager SHALL query the broker for order status
6. THE Trading Platform SHALL maintain separate audit trails for Paper Trading and Live Trading orders with timestamp and Trading Mode indicator
