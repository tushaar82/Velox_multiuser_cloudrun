# Project Structure

## Overview

This document describes the structure and organization of the Multi-User Algorithmic Trading Platform.

## Directory Structure

```
trading-platform/
├── api_gateway/                    # REST API Gateway Service
│   └── __init__.py
│
├── websocket_service/              # WebSocket Service for Real-time Updates
│   └── __init__.py
│
├── strategy_workers/               # Strategy Execution Workers
│   └── __init__.py
│
├── order_processor/                # Order Routing and Management
│   └── __init__.py
│
├── analytics_service/              # Performance Analytics and Reporting
│   └── __init__.py
│
├── market_data_engine/             # Market Data Processing
│   └── __init__.py
│
├── shared/                         # Shared Modules and Utilities
│   ├── config/                     # Configuration Management
│   │   ├── __init__.py
│   │   └── settings.py            # Pydantic settings with env var support
│   │
│   ├── database/                   # Database Connection Utilities
│   │   ├── __init__.py
│   │   └── connection.py          # SQLAlchemy with connection pooling
│   │
│   ├── redis/                      # Redis Connection Utilities
│   │   ├── __init__.py
│   │   └── connection.py          # Redis with cluster support
│   │
│   ├── models/                     # Shared Data Models
│   │   └── __init__.py
│   │
│   ├── utils/                      # Shared Utility Functions
│   │   ├── __init__.py
│   │   ├── health.py              # Health check utilities
│   │   └── logging_config.py      # Logging configuration
│   │
│   └── __init__.py
│
├── tests/                          # Test Suite
│   ├── __init__.py
│   └── test_infrastructure.py     # Infrastructure tests
│
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── docker-compose.yml              # Local development infrastructure
├── Dockerfile.base                 # Base Docker image
├── Makefile                        # Common tasks automation
├── pytest.ini                      # Pytest configuration
├── README.md                       # Project documentation
├── requirements.txt                # Python dependencies
├── setup.sh                        # Setup script
└── PROJECT_STRUCTURE.md           # This file
```

## Microservices

### 1. API Gateway (`api_gateway/`)
- Main entry point for REST API requests
- Handles authentication and authorization
- Routes requests to appropriate services
- Port: 8000 (default)

### 2. WebSocket Service (`websocket_service/`)
- Real-time bidirectional communication
- Market data streaming
- Position and order updates
- Notifications
- Port: 8001 (default)

### 3. Strategy Workers (`strategy_workers/`)
- Execute trading strategies
- Multi-timeframe analysis
- Signal generation
- Strategy state management

### 4. Order Processor (`order_processor/`)
- Order routing to brokers
- Paper trading simulation
- Order lifecycle management
- Trade execution tracking
- Port: 8003 (default)

### 5. Analytics Service (`analytics_service/`)
- Performance metrics calculation
- Report generation
- Chart data preparation
- Benchmark comparison
- Port: 8004 (default)

### 6. Market Data Engine (`market_data_engine/`)
- Tick data processing
- Candle formation (multiple timeframes)
- Indicator calculations
- Historical data management
- Port: 8002 (default)

## Shared Modules

### Configuration (`shared/config/`)
- Environment-based configuration
- Pydantic settings validation
- Support for .env files
- Google Cloud Secret Manager integration

**Key Features:**
- Type-safe configuration
- Automatic validation
- Environment variable mapping
- Database URL construction
- Redis URL construction

### Database (`shared/database/`)
- SQLAlchemy ORM integration
- Connection pooling (configurable)
- PgBouncer support
- Session management
- Health checks

**Key Features:**
- Pool size: 20 (configurable)
- Max overflow: 10 (configurable)
- Pool timeout: 30s (configurable)
- Pool recycle: 1 hour (configurable)
- Pre-ping enabled
- Context manager for transactions

### Redis (`shared/redis/`)
- Redis client management
- Cluster mode support
- Connection pooling
- Pub/Sub support
- JSON serialization helpers

**Key Features:**
- Standalone and cluster modes
- Max connections: 50 (configurable)
- Socket timeout: 5s (configurable)
- Health check support
- Automatic reconnection

### Utilities (`shared/utils/`)
- Health check utilities
- Logging configuration
- Common helper functions

## Infrastructure Services

### PostgreSQL
- Primary database for relational data
- Users, accounts, orders, trades, positions
- Port: 5432

### Redis
- Caching layer
- Real-time data storage
- Pub/Sub messaging
- Session management
- Port: 6379

### PgBouncer (Optional)
- Connection pooling at database level
- Recommended for production
- Port: 6432

### InfluxDB
- Time series database
- Historical candle data
- Market data storage
- Port: 8086

## Configuration

### Environment Variables

All configuration is managed through environment variables defined in `.env`:

**Application:**
- `APP_NAME`: Application name
- `ENVIRONMENT`: Environment (development/production/staging)
- `DEBUG`: Debug mode flag

**Database:**
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
- `USE_PGBOUNCER`, `PGBOUNCER_HOST`, `PGBOUNCER_PORT`

**Redis:**
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB`
- `REDIS_CLUSTER_MODE`, `REDIS_CLUSTER_NODES`
- `REDIS_MAX_CONNECTIONS`, `REDIS_SOCKET_TIMEOUT`

**Security:**
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS`
- `SESSION_TIMEOUT_MINUTES`, `MAX_LOGIN_ATTEMPTS`
- `ACCOUNT_LOCK_DURATION_MINUTES`

## Development Workflow

### Initial Setup
```bash
# Run setup script
bash setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Start Infrastructure
```bash
# Using make
make docker-up

# Or directly
docker-compose up -d
```

### Run Tests
```bash
# Using make
make test

# Or directly
pytest tests/ -v
```

### Code Quality
```bash
# Format code
make format

# Lint code
make lint
```

## Testing

### Test Organization
- `tests/test_infrastructure.py`: Infrastructure and configuration tests
- Future: Service-specific test files

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=shared --cov-report=html

# Specific test file
pytest tests/test_infrastructure.py -v
```

## Docker Deployment

### Base Image
The `Dockerfile.base` provides a common base for all services:
- Python 3.11
- System dependencies
- Python packages
- Shared modules
- Non-root user
- Health check support

### Service Images
Each service extends the base image with service-specific code.

## Next Steps

After completing Task 1 (infrastructure setup), the following tasks will build upon this foundation:

1. **Task 2**: Authentication and user management
2. **Task 3**: Broker connection management
3. **Task 4**: Market data engine implementation
4. **Task 5**: Strategy execution engine
5. And so on...

Each service will be implemented incrementally, building on the shared infrastructure.
