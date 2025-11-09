#!/bin/bash
# Run load tests with Artillery

set -e

# Configuration
TARGET_URL=${TARGET_URL:-"https://trading.example.com"}
TEST_TYPE=${1:-"all"}

echo "Running load tests against: $TARGET_URL"
echo "Test type: $TEST_TYPE"
echo ""

# Install Artillery if not installed
if ! command -v artillery &> /dev/null; then
    echo "Installing Artillery..."
    npm install -g artillery
fi

# Update target URL in config files
sed -i "s|https://trading.example.com|$TARGET_URL|g" load-tests/*.yml
sed -i "s|wss://trading.example.com|${TARGET_URL/https/wss}|g" load-tests/*.yml

case $TEST_TYPE in
  api)
    echo "Running API load tests..."
    artillery run load-tests/artillery-config.yml \
      --output load-tests/results/api-test-$(date +%Y%m%d-%H%M%S).json
    ;;
    
  websocket)
    echo "Running WebSocket load tests..."
    artillery run load-tests/websocket-test.yml \
      --output load-tests/results/ws-test-$(date +%Y%m%d-%H%M%S).json
    ;;
    
  all)
    echo "Running all load tests..."
    
    echo "1. API Load Tests..."
    artillery run load-tests/artillery-config.yml \
      --output load-tests/results/api-test-$(date +%Y%m%d-%H%M%S).json
    
    echo ""
    echo "2. WebSocket Load Tests..."
    artillery run load-tests/websocket-test.yml \
      --output load-tests/results/ws-test-$(date +%Y%m%d-%H%M%S).json
    ;;
    
  *)
    echo "Unknown test type: $TEST_TYPE"
    echo "Usage: $0 {api|websocket|all}"
    exit 1
    ;;
esac

echo ""
echo "Load tests complete!"
echo "Results saved in load-tests/results/"
