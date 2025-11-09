# Testing Environment Guide

This guide explains how to use the comprehensive testing environment for offline development and testing.

## Operating Modes

The platform supports four operating modes:

### 1. Live Mode
- **Use Case**: Production trading with real capital
- **Market Data**: Real-time from NSE
- **Order Execution**: Real orders through broker
- **Configuration**: `.env` (production)

### 2. Paper Mode
- **Use Case**: Practice trading without risk
- **Market Data**: Real-time from NSE
- **Order Execution**: Simulated (no real orders)
- **Configuration**: `.env` with `OPERATING_MODE=paper`

### 3. Replay Mode
- **Use Case**: Test strategies on historical data
- **Market Data**: Historical data replay
- **Order Execution**: Simulated
- **Configuration**: `.env.replay`

### 4. Simulated Mode
- **Use Case**: Development with synthetic data
- **Market Data**: Generated synthetic data
- **Order Execution**: Simulated
- **Configuration**: `.env.development`

## Quick Start

### Development Mode (Simulated)

```bash
# Copy development environment
cp .env.development .env

# Start all services with Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# Seed test data
python scripts/seed_data.py

# Access services
# API Gateway: http://localhost:8000
# WebSocket: http://localhost:8001
# Market Data: http://localhost:8002
```

### Replay Mode

```bash
# Copy replay environment
cp .env.replay .env

# Start services
docker-compose -f docker-compose.dev.yml up -d

# Download historical data (see Market Replay section)
python scripts/download_historical_data.py --days 30

# Start replay
# Use UI or API to control replay
```

### Testing Mode

```bash
# Copy testing environment
cp .env.testing .env

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Environment Configuration

### Switching Modes

Set the `OPERATING_MODE` environment variable:

```bash
# Development (simulated data)
export OPERATING_MODE=simulated

# Replay (historical data)
export OPERATING_MODE=replay

# Paper trading (real data, simulated orders)
export OPERATING_MODE=paper

# Live trading (real data, real orders)
export OPERATING_MODE=live
```

### Environment Files

- `.env.development` - Development with synthetic data
- `.env.replay` - Historical data replay
- `.env.testing` - Automated testing
- `.env.example` - Production template

## Test Data Management

### Seeding Test Data

```bash
# Create test users, accounts, and configuration
python scripts/seed_data.py
```

This creates:
- Admin user: `admin@tradingplatform.com` / `Admin@123`
- Trader 1: `trader1@example.com` / `Trader@123`
- Trader 2: `trader2@example.com` / `Trader@123`
- Investor 1: `investor1@example.com` / `Investor@123`
- Investor 2: `investor2@example.com` / `Investor@123`
- Risk limits and strategy limits
- Mock broker connections

### Exporting Test Scenarios

```bash
# Export current database state
python scripts/export_test_scenario.py my_scenario.json

# Share the scenario file with team members
```

### Importing Test Scenarios

```bash
# Import a test scenario
python scripts/import_test_scenario.py my_scenario.json

# This will recreate users, orders, positions, and configuration
```

## Docker Compose Services

### Development Setup

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down

# Reset everything (including data)
docker-compose -f docker-compose.dev.yml down -v
```

### Individual Services

```bash
# Start only database services
docker-compose -f docker-compose.dev.yml up -d postgres redis influxdb

# Start specific service
docker-compose -f docker-compose.dev.yml up -d api_gateway

# Restart a service
docker-compose -f docker-compose.dev.yml restart market_data_engine
```

## Database Management

### Accessing PostgreSQL

```bash
# Connect to database
docker exec -it trading_postgres_dev psql -U postgres -d trading_platform_dev

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Accessing Redis

```bash
# Connect to Redis
docker exec -it trading_redis_dev redis-cli

# View all keys
KEYS *

# Clear all data
FLUSHALL
```

### Accessing InfluxDB

```bash
# Access InfluxDB UI
# Open http://localhost:8086

# Or use CLI
docker exec -it trading_influxdb_dev influx
```

## Synthetic Data Generation

The simulator can generate realistic market data:

```python
from market_data_engine.simulator import MarketDataSimulator

simulator = MarketDataSimulator()

# Generate 10,000 ticks for RELIANCE
simulator.generate_synthetic_data(
    symbol="RELIANCE",
    start_price=2500.0,
    num_ticks=10000,
    volatility=0.02,  # 2% volatility
    trend=0.0001      # Slight upward trend
)

# Start replay at 10x speed
simulator.set_speed(10.0)
simulator.start_replay(["RELIANCE"])
```

## Testing Best Practices

### Unit Tests

```bash
# Run all unit tests
pytest tests/ -v -m "not integration"

# Run specific test file
pytest tests/test_authentication.py -v

# Run with coverage
pytest tests/ --cov=shared --cov=api_gateway
```

### Integration Tests

```bash
# Run integration tests
pytest tests/ -v -m integration

# Run end-to-end tests
pytest tests/test_e2e_user_flows.py -v
```

### Performance Testing

```bash
# Run load tests
cd load-tests
./run-tests.sh

# Analyze results
./analyze-results.sh
```

## Troubleshooting

### Services Won't Start

```bash
# Check service logs
docker-compose -f docker-compose.dev.yml logs <service_name>

# Check if ports are in use
lsof -i :8000  # API Gateway
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Reset everything
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

### Database Connection Issues

```bash
# Wait for database to be ready
docker-compose -f docker-compose.dev.yml up -d postgres
sleep 10

# Run migrations
alembic upgrade head

# Seed data
python scripts/seed_data.py
```

### Simulator Not Working

```bash
# Check market data engine logs
docker-compose -f docker-compose.dev.yml logs market_data_engine

# Verify operating mode
echo $OPERATING_MODE

# Restart market data engine
docker-compose -f docker-compose.dev.yml restart market_data_engine
```

## Advanced Configuration

### Custom Simulator Settings

Edit `.env.development`:

```bash
# Simulator configuration
SIMULATOR_DEFAULT_SPEED=1.0
SIMULATOR_AUTO_START=true
SIMULATOR_SYMBOLS=RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK
SIMULATOR_START_PRICE=1000
SIMULATOR_NUM_TICKS=10000
SIMULATOR_VOLATILITY=0.02
SIMULATOR_TREND=0.0
```

### Custom Database Configuration

```bash
# Use different database for testing
DB_NAME=trading_platform_custom
DB_PORT=5433

# Use different Redis database
REDIS_DB=3
```

### Performance Tuning

```bash
# Increase connection pools
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20
REDIS_MAX_CONNECTIONS=100

# Adjust timeouts
DB_POOL_TIMEOUT=60
REDIS_SOCKET_TIMEOUT=10
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: trading_platform_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        env:
          OPERATING_MODE: simulated
          DB_HOST: localhost
          REDIS_HOST: localhost
        run: |
          pytest tests/ -v --cov=.
```

## Support

For issues or questions:
1. Check logs: `docker-compose -f docker-compose.dev.yml logs`
2. Review this guide
3. Check the main README.md
4. Contact the development team
