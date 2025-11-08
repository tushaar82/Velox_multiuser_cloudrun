# Multi-User Algorithmic Trading Platform

A comprehensive algorithmic trading platform for the National Stock Exchange (NSE) of India with support for multiple users, brokers, and real-time strategy execution.

## Project Structure

```
.
├── api_gateway/              # REST API gateway service
├── websocket_service/        # Real-time WebSocket service
├── strategy_workers/         # Strategy execution workers
├── order_processor/          # Order routing and management
├── analytics_service/        # Performance analytics and reporting
├── market_data_engine/       # Market data processing and candle formation
├── shared/                   # Shared modules and utilities
│   ├── config/              # Configuration management
│   ├── database/            # Database connection utilities
│   ├── redis/               # Redis connection utilities
│   ├── models/              # Shared data models
│   └── utils/               # Shared utility functions
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Local development environment
└── Dockerfile.base          # Base Docker image
```

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- InfluxDB 2.7+
- Docker and Docker Compose (for local development)

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd trading-platform
```

### 2. Set up Python virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Start infrastructure services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- PgBouncer on port 6432
- InfluxDB on port 8086

### 6. Verify services are running

```bash
docker-compose ps
```

## Configuration

The platform uses environment variables for configuration. Key settings include:

### Database Configuration
- `DB_HOST`: PostgreSQL host (default: localhost)
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name (default: trading_platform)
- `DB_POOL_SIZE`: Connection pool size (default: 20)

### Redis Configuration
- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_CLUSTER_MODE`: Enable cluster mode (default: false)
- `REDIS_MAX_CONNECTIONS`: Max connections (default: 50)

### PgBouncer (Optional)
- `USE_PGBOUNCER`: Enable PgBouncer (default: false)
- `PGBOUNCER_HOST`: PgBouncer host
- `PGBOUNCER_PORT`: PgBouncer port (default: 6432)

### Security
- `JWT_SECRET_KEY`: Secret key for JWT tokens (change in production!)
- `SESSION_TIMEOUT_MINUTES`: Session timeout (default: 30)
- `MAX_LOGIN_ATTEMPTS`: Max failed login attempts (default: 3)

## Database Connection Pooling

The platform uses SQLAlchemy with connection pooling for efficient database access:

- **Pool Size**: 20 connections (configurable)
- **Max Overflow**: 10 additional connections
- **Pool Timeout**: 30 seconds
- **Pool Recycle**: 3600 seconds (1 hour)
- **Pre-ping**: Enabled (verifies connections before use)

### PgBouncer Integration

For production deployments, PgBouncer provides additional connection pooling:

1. Set `USE_PGBOUNCER=true` in .env
2. Configure `PGBOUNCER_HOST` and `PGBOUNCER_PORT`
3. PgBouncer will handle connection pooling at the database level

## Redis Connection Management

The platform supports both standalone and cluster Redis deployments:

### Standalone Mode (Default)
```env
REDIS_CLUSTER_MODE=false
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Cluster Mode
```env
REDIS_CLUSTER_MODE=true
REDIS_CLUSTER_NODES=node1:6379,node2:6379,node3:6379
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Docker Deployment

### Build base image

```bash
docker build -f Dockerfile.base -t trading-platform-base:latest .
```

### Build service images

Each service will have its own Dockerfile that extends the base image:

```dockerfile
FROM trading-platform-base:latest
COPY <service_name>/ /app/<service_name>/
CMD ["python", "-m", "<service_name>.main"]
```

## Architecture

The platform follows a microservices architecture:

1. **API Gateway**: Main entry point for REST API requests
2. **WebSocket Service**: Real-time updates and bidirectional communication
3. **Strategy Workers**: Execute trading strategies and generate signals
4. **Order Processor**: Handle order routing and execution
5. **Analytics Service**: Calculate performance metrics and reports
6. **Market Data Engine**: Process tick data and maintain candles

All services share common utilities through the `shared/` module.

## License

[Your License Here]
