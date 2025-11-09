#!/bin/bash
# install.sh - Install dependencies and setup the trading platform

set -e  # Exit on error

echo "=========================================="
echo "Trading Platform - Installation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${YELLOW}Warning: This script is optimized for Linux. Some features may not work on other systems.${NC}"
fi

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python 3.10 or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Check Docker
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker found and running${NC}"

# Check Docker Compose
echo "Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo -e "${GREEN}✓ Docker Compose v1 found${NC}"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${GREEN}✓ Docker Compose v2 found${NC}"
else
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Setup environment files
echo ""
echo "Setting up environment files..."
if [ ! -f ".env.development" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env.development
        echo -e "${GREEN}✓ Created .env.development from .env.example${NC}"
    else
        echo -e "${YELLOW}Warning: .env.example not found${NC}"
    fi
else
    echo -e "${YELLOW}.env.development already exists${NC}"
fi

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data/historical
mkdir -p data/backtest
mkdir -p data/exports
echo -e "${GREEN}✓ Directories created${NC}"

# Pull Docker images
echo ""
echo "Pulling Docker images..."
$DOCKER_COMPOSE pull
echo -e "${GREEN}✓ Docker images pulled${NC}"

# Start infrastructure services
echo ""
echo "Starting infrastructure services (PostgreSQL, Redis, InfluxDB)..."
$DOCKER_COMPOSE up -d postgres redis influxdb
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo "Checking service health..."
if $DOCKER_COMPOSE ps | grep -q "unhealthy"; then
    echo -e "${YELLOW}Warning: Some services may not be healthy yet. Waiting...${NC}"
    sleep 10
fi

# Run database migrations
echo ""
echo "Running database migrations..."
if alembic current &> /dev/null; then
    alembic upgrade head
    echo -e "${GREEN}✓ Database migrations completed${NC}"
else
    echo -e "${YELLOW}Warning: Alembic not configured or database not accessible${NC}"
    echo "You may need to run migrations manually: alembic upgrade head"
fi

# Load default symbol mappings (if script exists)
if [ -f "scripts/load_default_mappings.py" ]; then
    echo ""
    echo "Loading default symbol mappings..."
    python3 scripts/load_default_mappings.py || echo -e "${YELLOW}Warning: Could not load default mappings${NC}"
fi

# Install frontend dependencies (if frontend exists)
if [ -d "frontend" ]; then
    echo ""
    echo "Checking frontend dependencies..."
    if command -v npm &> /dev/null; then
        echo "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    else
        echo -e "${YELLOW}Warning: npm not found. Skipping frontend setup.${NC}"
        echo "Install Node.js to build the frontend: https://nodejs.org/"
    fi
fi

# Create test data (optional)
echo ""
read -p "Do you want to create test data? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "scripts/seed_data.py" ]; then
        echo "Creating test data..."
        python3 scripts/seed_data.py
        echo -e "${GREEN}✓ Test data created${NC}"
    else
        echo -e "${YELLOW}Warning: seed_data.py not found${NC}"
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Installation completed successfully!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review and update .env.development with your configuration"
echo "2. Run './run.sh' to start all services"
echo "3. Run './test.sh' to run tests"
echo "4. Access the application at http://localhost:3000"
echo ""
echo "For more information, see README.md"
echo ""
