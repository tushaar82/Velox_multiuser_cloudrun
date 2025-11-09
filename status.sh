#!/bin/bash
# status.sh - Check status of all trading platform services

echo "=========================================="
echo "Trading Platform - Service Status"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Docker services
echo -e "${BLUE}Infrastructure Services:${NC}"
echo "----------------------------------------"

check_docker_service() {
    local service=$1
    if docker-compose ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✓${NC} $service is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running"
        return 1
    fi
}

check_docker_service "postgres"
check_docker_service "redis"
check_docker_service "influxdb"
check_docker_service "pgbouncer"

echo ""

# Check backend services
echo -e "${BLUE}Backend Services:${NC}"
echo "----------------------------------------"

check_service() {
    local service_name=$1
    local pid_file="logs/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            # Get memory usage
            mem=$(ps -p $pid -o rss= | awk '{printf "%.1f MB", $1/1024}')
            # Get CPU usage
            cpu=$(ps -p $pid -o %cpu= | awk '{printf "%.1f%%", $1}')
            echo -e "${GREEN}✓${NC} $service_name (PID: $pid, CPU: $cpu, MEM: $mem)"
            return 0
        else
            echo -e "${RED}✗${NC} $service_name (stale PID file)"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} $service_name (not running)"
        return 1
    fi
}

check_service "api_gateway"
check_service "websocket_service"
check_service "market_data_engine"
check_service "order_processor"
check_service "strategy_workers"
check_service "analytics_service"

# Check frontend
if [ -f "logs/frontend.pid" ]; then
    echo ""
    echo -e "${BLUE}Frontend:${NC}"
    echo "----------------------------------------"
    check_service "frontend"
fi

echo ""

# Check ports
echo -e "${BLUE}Port Status:${NC}"
echo "----------------------------------------"

check_port() {
    local port=$1
    local service=$2
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "${GREEN}✓${NC} Port $port ($service) is listening"
        return 0
    else
        echo -e "${RED}✗${NC} Port $port ($service) is not listening"
        return 1
    fi
}

check_port "5000" "API Gateway"
check_port "5001" "WebSocket"
check_port "5002" "Analytics"
check_port "5432" "PostgreSQL"
check_port "6379" "Redis"
check_port "8086" "InfluxDB"

echo ""

# Check database connectivity
echo -e "${BLUE}Database Connectivity:${NC}"
echo "----------------------------------------"

if command -v psql &> /dev/null; then
    if PGPASSWORD=postgres psql -h localhost -U postgres -d trading_platform -c "SELECT 1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL connection successful"
    else
        echo -e "${RED}✗${NC} PostgreSQL connection failed"
    fi
else
    echo -e "${YELLOW}⚠${NC} psql not installed, skipping database check"
fi

if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓${NC} Redis connection successful"
    else
        echo -e "${RED}✗${NC} Redis connection failed"
    fi
else
    echo -e "${YELLOW}⚠${NC} redis-cli not installed, skipping Redis check"
fi

echo ""

# Check disk space
echo -e "${BLUE}System Resources:${NC}"
echo "----------------------------------------"

# Disk space
df_output=$(df -h . | tail -1)
disk_usage=$(echo $df_output | awk '{print $5}' | sed 's/%//')
disk_avail=$(echo $df_output | awk '{print $4}')

if [ $disk_usage -lt 80 ]; then
    echo -e "${GREEN}✓${NC} Disk space: $disk_avail available (${disk_usage}% used)"
elif [ $disk_usage -lt 90 ]; then
    echo -e "${YELLOW}⚠${NC} Disk space: $disk_avail available (${disk_usage}% used)"
else
    echo -e "${RED}✗${NC} Disk space: $disk_avail available (${disk_usage}% used) - LOW!"
fi

# Memory
if command -v free &> /dev/null; then
    mem_total=$(free -h | grep Mem | awk '{print $2}')
    mem_used=$(free -h | grep Mem | awk '{print $3}')
    mem_percent=$(free | grep Mem | awk '{printf "%.0f", ($3/$2) * 100}')
    
    if [ $mem_percent -lt 80 ]; then
        echo -e "${GREEN}✓${NC} Memory: $mem_used / $mem_total (${mem_percent}% used)"
    elif [ $mem_percent -lt 90 ]; then
        echo -e "${YELLOW}⚠${NC} Memory: $mem_used / $mem_total (${mem_percent}% used)"
    else
        echo -e "${RED}✗${NC} Memory: $mem_used / $mem_total (${mem_percent}% used) - HIGH!"
    fi
fi

echo ""

# Recent errors in logs
echo -e "${BLUE}Recent Errors (last 5 minutes):${NC}"
echo "----------------------------------------"

if [ -d "logs" ]; then
    error_count=$(find logs -name "*.log" -mmin -5 -exec grep -i "error\|exception\|failed" {} \; 2>/dev/null | wc -l)
    
    if [ $error_count -eq 0 ]; then
        echo -e "${GREEN}✓${NC} No errors found in recent logs"
    elif [ $error_count -lt 10 ]; then
        echo -e "${YELLOW}⚠${NC} $error_count errors found in recent logs"
        echo "  Run: grep -i 'error' logs/*.log | tail -10"
    else
        echo -e "${RED}✗${NC} $error_count errors found in recent logs"
        echo "  Run: grep -i 'error' logs/*.log | tail -20"
    fi
else
    echo -e "${YELLOW}⚠${NC} Logs directory not found"
fi

echo ""

# Service URLs
echo -e "${BLUE}Service URLs:${NC}"
echo "----------------------------------------"
echo "  Frontend:    http://localhost:3000"
echo "  API Gateway: http://localhost:5000"
echo "  WebSocket:   http://localhost:5001"
echo "  Analytics:   http://localhost:5002"
echo "  InfluxDB:    http://localhost:8086"

echo ""

# Quick actions
echo -e "${BLUE}Quick Actions:${NC}"
echo "----------------------------------------"
echo "  View logs:       tail -f logs/<service>.log"
echo "  Restart service: kill \$(cat logs/<service>.pid) && ./run.sh"
echo "  Stop all:        ./stop.sh"
echo "  Run tests:       ./test.sh"

echo ""
echo "=========================================="
