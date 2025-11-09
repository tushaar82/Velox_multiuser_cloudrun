#!/bin/bash
# test.sh - Run tests for the trading platform

set -e  # Exit on error

echo "=========================================="
echo "Trading Platform - Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-yes}"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}Error: Virtual environment not found. Run ./install.sh first${NC}"
    exit 1
fi

# Detect docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}Error: Docker Compose not found${NC}"
    exit 1
fi

# Ensure test environment is set up
export TESTING=true
export $(grep -v '^#' .env.testing | xargs) 2>/dev/null || true

# Start test infrastructure if needed
echo "Starting test infrastructure..."
$DOCKER_COMPOSE up -d postgres redis influxdb
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Create test database if it doesn't exist
echo "Creating test database..."
docker exec trading_postgres psql -U postgres -c "DROP DATABASE IF EXISTS trading_platform_test;" 2>/dev/null || true
docker exec trading_postgres psql -U postgres -c "CREATE DATABASE trading_platform_test;" 2>/dev/null || echo -e "${YELLOW}Test database may already exist${NC}"

# Run database migrations for test database
echo "Setting up test database schema..."
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/trading_platform_test"
alembic upgrade head 2>/dev/null || echo -e "${YELLOW}Warning: Could not run migrations (this may be OK if schema exists)${NC}"

echo ""
echo -e "${BLUE}Running tests...${NC}"
echo ""

# Function to run tests with coverage
run_tests() {
    local test_path=$1
    local test_name=$2
    
    echo "=========================================="
    echo "Running ${test_name}"
    echo "=========================================="
    
    if [ "$COVERAGE" = "yes" ]; then
        pytest $test_path -v --cov=. --cov-report=term-missing --cov-report=html
    else
        pytest $test_path -v
    fi
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ ${test_name} passed${NC}"
    else
        echo -e "${RED}✗ ${test_name} failed${NC}"
        return $exit_code
    fi
    
    echo ""
}

# Run tests based on type
case $TEST_TYPE in
    "all")
        echo "Running all tests..."
        echo -e "${YELLOW}Note: Running smoke tests (quick validation)${NC}"
        run_tests "tests/test_trailing_stop_smoke.py tests/test_trailing_stop_integration.py" "Smoke Tests"
        ;;
    
    "unit")
        echo "Running unit tests..."
        run_tests "tests/test_trailing_stop_smoke.py" "Unit Tests (Smoke)"
        ;;
    
    "integration")
        echo "Running integration tests..."
        run_tests "tests/test_integration*.py tests/test_*_integration.py" "Integration Tests"
        ;;
    
    "e2e")
        echo "Running end-to-end tests..."
        run_tests "tests/test_e2e*.py" "End-to-End Tests"
        ;;
    
    "position")
        echo "Running position management tests..."
        run_tests "tests/test_position*.py" "Position Management Tests"
        ;;
    
    "trailing-stop")
        echo "Running trailing stop tests..."
        run_tests "tests/test_trailing_stop*.py" "Trailing Stop Tests"
        ;;
    
    "security")
        echo "Running security tests..."
        run_tests "tests/test_security*.py" "Security Tests"
        ;;
    
    "requirements")
        echo "Running requirements validation tests..."
        run_tests "tests/test_requirements*.py" "Requirements Validation Tests"
        ;;
    
    "quick")
        echo "Running quick tests (no coverage)..."
        COVERAGE="no"
        pytest tests/ -v -m "not slow" --tb=short
        ;;
    
    *)
        echo -e "${RED}Error: Invalid test type '$TEST_TYPE'${NC}"
        echo ""
        echo "Usage: ./test.sh [test_type] [coverage]"
        echo ""
        echo "Test types:"
        echo "  all              - Run all tests (default)"
        echo "  unit             - Run unit tests only"
        echo "  integration      - Run integration tests only"
        echo "  e2e              - Run end-to-end tests only"
        echo "  position         - Run position management tests"
        echo "  trailing-stop    - Run trailing stop tests"
        echo "  security         - Run security tests"
        echo "  requirements     - Run requirements validation tests"
        echo "  quick            - Run quick tests without coverage"
        echo ""
        echo "Coverage:"
        echo "  yes              - Generate coverage report (default)"
        echo "  no               - Skip coverage report"
        echo ""
        echo "Examples:"
        echo "  ./test.sh                    # Run all tests with coverage"
        echo "  ./test.sh unit               # Run unit tests with coverage"
        echo "  ./test.sh integration no     # Run integration tests without coverage"
        echo "  ./test.sh quick              # Run quick tests"
        exit 1
        ;;
esac

# Test exit code
TEST_EXIT_CODE=$?

# Display coverage report location
if [ "$COVERAGE" = "yes" ] && [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Coverage report generated:"
    echo "  HTML: htmlcov/index.html"
    echo "  Terminal output above"
    echo "=========================================="
    echo ""
    
    # Optional: Open coverage report
    read -p "Do you want to open the coverage report in browser? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html
        elif command -v open &> /dev/null; then
            open htmlcov/index.html
        else
            echo "Please open htmlcov/index.html manually"
        fi
    fi
fi

# Summary
echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
else
    echo -e "${RED}Some tests failed!${NC}"
fi
echo "=========================================="
echo ""

# Cleanup
echo "Cleaning up test infrastructure..."
$DOCKER_COMPOSE down

exit $TEST_EXIT_CODE
