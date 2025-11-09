#!/bin/bash
# run.sh - Start all services of the trading platform

set -e  # Exit on error

echo "=========================================="
echo "Trading Platform - Starting Services"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default mode
MODE="${1:-development}"

# Validate mode
if [[ ! "$MODE" =~ ^(development|testing|replay|production)$ ]]; then
    echo -e "${RED}Error: Invalid mode '$MODE'${NC}"
    echo "Usage: ./run.sh [development|testing|replay|production]"
    exit 1
fi

echo -e "${BLUE}Starting in ${MODE} mode...${NC}"
echo ""

# Detect docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}Error: Docker Compose not found${NC}"
    exit 1
fi

# Load environment file
ENV_FILE=".env.${MODE}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: $ENV_FILE not found, using .env.development${NC}"
    ENV_FILE=".env.development"
fi

# Export environment variables (handle values with spaces)
set -a
source $ENV_FILE 2>/dev/null || true
set +a

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}Warning: Virtual environment not found. Run ./install.sh first${NC}"
fi

# Start infrastructure services
echo ""
echo "Starting infrastructure services..."
$DOCKER_COMPOSE up -d postgres redis influxdb pgbouncer

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 5

# Check if services are healthy
if ! $DOCKER_COMPOSE ps | grep -q "postgres.*healthy"; then
    echo -e "${YELLOW}Warning: PostgreSQL may not be ready yet${NC}"
fi

if ! $DOCKER_COMPOSE ps | grep -q "redis.*healthy"; then
    echo -e "${YELLOW}Warning: Redis may not be ready yet${NC}"
fi

echo -e "${GREEN}✓ Infrastructure services started${NC}"

# Create database if it doesn't exist
echo ""
echo "Setting up database..."
docker exec trading_postgres psql -U postgres -c "CREATE DATABASE ${DB_NAME:-trading_platform_dev};" 2>/dev/null || echo -e "${YELLOW}Database may already exist${NC}"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head 2>/dev/null || echo -e "${YELLOW}Warning: Migration check failed (this may be OK)${NC}"

# Create logs directory
mkdir -p logs

# Start backend services
echo ""
echo "Starting backend services..."

# Function to start a service in background
start_service() {
    local service_name=$1
    local service_path=$2
    local service_module=$3
    local log_file="logs/${service_name}.log"
    local project_root=$(pwd)
    
    echo "Starting ${service_name}..."
    # Run from project root with proper module path
    PYTHONPATH="${project_root}:${PYTHONPATH}" nohup python3 -m ${service_path}.${service_module} > "${log_file}" 2>&1 &
    echo $! > "logs/${service_name}.pid"
    echo -e "${GREEN}✓ ${service_name} started (PID: $(cat logs/${service_name}.pid))${NC}"
}

# Start API Gateway
start_service "api_gateway" "api_gateway" "app"

# Start WebSocket Service
start_service "websocket_service" "websocket_service" "app"

# Start Market Data Engine
start_service "market_data_engine" "market_data_engine" "app"

# Start Order Processor
start_service "order_processor" "order_processor" "app"

# Start Strategy Workers
start_service "strategy_workers" "strategy_workers" "app"

# Start Analytics Service
start_service "analytics_service" "analytics_service" "app"

# Wait a moment for services to initialize
sleep 3

# Check if services are running
echo ""
echo "Checking service status..."
for service in api_gateway websocket_service market_data_engine order_processor strategy_workers analytics_service; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat "logs/${service}.pid")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${service} is running (PID: ${pid})${NC}"
        else
            echo -e "${RED}✗ ${service} failed to start${NC}"
            echo "Check logs/${service}.log for details"
        fi
    fi
done

# Start frontend (if in development mode)
if [ "$MODE" = "development" ] && [ -d "frontend" ]; then
    echo ""
    echo "Starting frontend development server..."
    if command -v npm &> /dev/null; then
        cd frontend
        nohup npm run dev > ../logs/frontend.log 2>&1 &
        echo $! > ../logs/frontend.pid
        cd ..
        echo -e "${GREEN}✓ Frontend started (PID: $(cat logs/frontend.pid))${NC}"
    else
        echo -e "${YELLOW}Warning: npm not found. Frontend not started.${NC}"
    fi
fi

# Display service URLs
echo ""
echo "=========================================="
echo -e "${GREEN}All services started successfully!${NC}"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  API Gateway:        http://localhost:5000"
echo "  WebSocket Service:  http://localhost:5001"
echo "  Analytics Service:  http://localhost:5002"
if [ "$MODE" = "development" ]; then
    echo "  Frontend:           http://localhost:3000"
fi
echo ""
echo "Infrastructure:"
echo "  PostgreSQL:         localhost:5432"
echo "  Redis:              localhost:6379"
echo "  InfluxDB:           http://localhost:8086"
echo ""
echo "Logs are available in the logs/ directory"
echo ""
echo "To stop all services, run: ./stop.sh"
echo "To view logs: tail -f logs/<service_name>.log"
echo ""

# Optional: Follow logs
read -p "Do you want to follow the logs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Following logs (Ctrl+C to exit)..."
    tail -f logs/*.log
fi
