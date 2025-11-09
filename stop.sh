#!/bin/bash
# stop.sh - Stop all services of the trading platform

echo "=========================================="
echo "Trading Platform - Stopping Services"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="logs/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping ${service_name} (PID: ${pid})..."
            kill $pid
            
            # Wait for process to stop
            for i in {1..10}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ ${service_name} stopped${NC}"
                    rm "$pid_file"
                    return 0
                fi
                sleep 1
            done
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${YELLOW}Force stopping ${service_name}...${NC}"
                kill -9 $pid
                rm "$pid_file"
                echo -e "${GREEN}✓ ${service_name} force stopped${NC}"
            fi
        else
            echo -e "${YELLOW}${service_name} is not running${NC}"
            rm "$pid_file"
        fi
    else
        echo -e "${YELLOW}${service_name} PID file not found${NC}"
    fi
}

# Stop backend services
echo "Stopping backend services..."
stop_service "api_gateway"
stop_service "websocket_service"
stop_service "market_data_engine"
stop_service "order_processor"
stop_service "strategy_workers"
stop_service "analytics_service"

# Stop frontend
if [ -f "logs/frontend.pid" ]; then
    echo ""
    echo "Stopping frontend..."
    stop_service "frontend"
fi

# Stop Docker services
echo ""
echo "Stopping infrastructure services..."
docker-compose down

echo -e "${GREEN}✓ Infrastructure services stopped${NC}"

# Optional: Clean up logs
echo ""
read -p "Do you want to clean up log files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning up logs..."
    rm -f logs/*.log
    rm -f logs/*.pid
    echo -e "${GREEN}✓ Logs cleaned${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}All services stopped successfully!${NC}"
echo "=========================================="
echo ""
