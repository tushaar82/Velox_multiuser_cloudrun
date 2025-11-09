# Trading Platform - Scripts Guide

This guide explains how to use the management scripts to run the complete trading platform system.

## Overview

The platform includes four main scripts for managing the system:

- **install.sh** - Install dependencies and setup the environment
- **run.sh** - Start all services
- **stop.sh** - Stop all services
- **test.sh** - Run the test suite

## Prerequisites

Before running the scripts, ensure you have:

- **Linux** operating system (Ubuntu 20.04+ recommended)
- **Python 3.10+** installed
- **Docker** and **Docker Compose** installed and running
- **Node.js 16+** (optional, for frontend)
- **Git** (for cloning the repository)

## Quick Start

```bash
# 1. Install dependencies and setup
./install.sh

# 2. Start all services
./run.sh

# 3. Access the application
# Frontend: http://localhost:3000
# API: http://localhost:5000

# 4. Stop all services when done
./stop.sh
```

## Detailed Usage

### 1. install.sh - Installation Script

Installs all dependencies and sets up the environment.

```bash
./install.sh
```

**What it does:**
- Checks system requirements (Python, Docker, Docker Compose)
- Creates Python virtual environment
- Installs Python dependencies from requirements.txt
- Sets up environment files (.env.development)
- Creates necessary directories (logs, data)
- Pulls Docker images
- Starts infrastructure services (PostgreSQL, Redis, InfluxDB)
- Runs database migrations
- Loads default symbol mappings
- Installs frontend dependencies (if npm available)
- Optionally creates test data

**First-time setup:**
After installation, review and update `.env.development` with your configuration:
```bash
nano .env.development
```

### 2. run.sh - Start Services

Starts all platform services in the specified mode.

```bash
./run.sh [mode]
```

**Modes:**
- `development` (default) - Development mode with hot reload
- `testing` - Testing mode with test database
- `replay` - Replay mode for backtesting with historical data
- `production` - Production mode with optimizations

**Examples:**
```bash
# Start in development mode (default)
./run.sh

# Start in testing mode
./run.sh testing

# Start in replay mode for backtesting
./run.sh replay

# Start in production mode
./run.sh production
```

**What it does:**
- Loads environment variables from `.env.[mode]`
- Activates Python virtual environment
- Starts infrastructure services (PostgreSQL, Redis, InfluxDB, PgBouncer)
- Runs database migrations
- Starts backend services:
  - API Gateway (port 5000)
  - WebSocket Service (port 5001)
  - Market Data Engine
  - Order Processor
  - Strategy Workers
  - Analytics Service (port 5002)
- Starts frontend development server (port 3000) in development mode
- Creates PID files in logs/ directory
- Displays service URLs and status

**Service Logs:**
All service logs are stored in the `logs/` directory:
```bash
# View specific service log
tail -f logs/api_gateway.log

# View all logs
tail -f logs/*.log

# View last 100 lines
tail -n 100 logs/order_processor.log
```

**Service Status:**
Check if services are running:
```bash
# Check all PIDs
ls -la logs/*.pid

# Check specific service
ps -p $(cat logs/api_gateway.pid)
```

### 3. stop.sh - Stop Services

Stops all running services gracefully.

```bash
./stop.sh
```

**What it does:**
- Stops all backend services (using PID files)
- Stops frontend development server
- Stops Docker infrastructure services
- Optionally cleans up log files
- Removes PID files

**Force stop:**
If services don't stop gracefully, the script will force kill them after 10 seconds.

**Clean logs:**
When prompted, you can choose to clean up log files:
```bash
Do you want to clean up log files? (y/N) y
```

### 4. test.sh - Test Suite

Runs the platform test suite with various options.

```bash
./test.sh [test_type] [coverage]
```

**Test Types:**
- `all` (default) - Run all tests
- `unit` - Run unit tests only
- `integration` - Run integration tests only
- `e2e` - Run end-to-end tests only
- `position` - Run position management tests
- `trailing-stop` - Run trailing stop tests
- `security` - Run security tests
- `requirements` - Run requirements validation tests
- `quick` - Run quick tests without coverage

**Coverage:**
- `yes` (default) - Generate coverage report
- `no` - Skip coverage report

**Examples:**
```bash
# Run all tests with coverage
./test.sh

# Run unit tests only
./test.sh unit

# Run integration tests without coverage
./test.sh integration no

# Run trailing stop tests
./test.sh trailing-stop

# Run quick tests (no coverage, no slow tests)
./test.sh quick

# Run security tests with coverage
./test.sh security yes
```

**What it does:**
- Activates Python virtual environment
- Sets up test environment variables
- Starts test infrastructure (PostgreSQL, Redis, InfluxDB)
- Runs database migrations for test database
- Executes pytest with specified options
- Generates coverage report (HTML and terminal)
- Displays test results and coverage summary
- Cleans up test infrastructure

**Coverage Report:**
After running tests with coverage, view the HTML report:
```bash
# Open in browser (Linux)
xdg-open htmlcov/index.html

# Or manually open
firefox htmlcov/index.html
```

## Service Architecture

### Infrastructure Services (Docker)
- **PostgreSQL** (port 5432) - Main database
- **PgBouncer** (port 6432) - Connection pooler
- **Redis** (port 6379) - Cache and pub/sub
- **InfluxDB** (port 8086) - Time series data

### Backend Services (Python)
- **API Gateway** (port 5000) - REST API endpoints
- **WebSocket Service** (port 5001) - Real-time updates
- **Market Data Engine** - Market data processing
- **Order Processor** - Order execution and position management
- **Strategy Workers** - Strategy execution
- **Analytics Service** (port 5002) - Analytics and reporting

### Frontend (React)
- **Development Server** (port 3000) - React application

## Environment Files

The platform uses different environment files for different modes:

- `.env.development` - Development configuration
- `.env.testing` - Testing configuration
- `.env.replay` - Replay/backtesting configuration
- `.env.production` - Production configuration (not included in repo)

**Key environment variables:**
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_platform
REDIS_URL=redis://localhost:6379/0
INFLUXDB_URL=http://localhost:8086

# Services
API_GATEWAY_PORT=5000
WEBSOCKET_PORT=5001
ANALYTICS_PORT=5002

# Mode
TRADING_MODE=development  # development, testing, replay, production

# Broker API (for live trading)
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_CODE=your_client_code
```

## Troubleshooting

### Services won't start

1. Check if ports are already in use:
```bash
sudo netstat -tulpn | grep -E '5000|5001|5002|5432|6379|8086'
```

2. Check Docker services:
```bash
docker-compose ps
docker-compose logs postgres
```

3. Check service logs:
```bash
tail -f logs/*.log
```

### Database connection errors

1. Ensure PostgreSQL is running:
```bash
docker-compose ps postgres
```

2. Test connection:
```bash
psql -h localhost -U postgres -d trading_platform
```

3. Run migrations:
```bash
source venv/bin/activate
alembic upgrade head
```

### Python dependency errors

1. Reinstall dependencies:
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

2. Clear pip cache:
```bash
pip cache purge
```

### Docker issues

1. Restart Docker daemon:
```bash
sudo systemctl restart docker
```

2. Clean up Docker:
```bash
docker-compose down -v
docker system prune -a
```

3. Rebuild images:
```bash
docker-compose build --no-cache
```

### Port conflicts

If default ports are in use, update them in your `.env` file:
```bash
API_GATEWAY_PORT=5010
WEBSOCKET_PORT=5011
ANALYTICS_PORT=5012
```

## Development Workflow

### Daily Development

```bash
# Start services
./run.sh development

# Make code changes...

# Run tests
./test.sh unit

# View logs
tail -f logs/api_gateway.log

# Stop services
./stop.sh
```

### Testing Changes

```bash
# Run specific tests
./test.sh trailing-stop

# Run quick tests during development
./test.sh quick

# Run full test suite before commit
./test.sh all
```

### Debugging

```bash
# Start services
./run.sh development

# In another terminal, attach to service
tail -f logs/order_processor.log

# Or use Python debugger
source venv/bin/activate
python3 -m pdb order_processor/app.py
```

## Production Deployment

For production deployment, see:
- `DOCKER_DEPLOYMENT.md` - Docker deployment guide
- `infrastructure/` - Infrastructure as code
- `cloudbuild.yaml` - CI/CD configuration

**Production checklist:**
1. Update `.env.production` with production values
2. Set strong passwords and secrets
3. Configure SSL/TLS certificates
4. Set up monitoring and alerting
5. Configure backup strategy
6. Review security settings
7. Test disaster recovery procedures

## Additional Resources

- **README.md** - Project overview and documentation
- **PROJECT_STRUCTURE.md** - Codebase structure
- **API_POSITION_ENDPOINTS.md** - API documentation
- **TESTING_ENVIRONMENT.md** - Testing guide
- **OFFLINE_TESTING_IMPLEMENTATION.md** - Offline testing setup

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review the troubleshooting section above
3. Check existing issues in the repository
4. Create a new issue with:
   - Error messages
   - Relevant log files
   - Steps to reproduce
   - System information

## License

See LICENSE file for details.
