#!/bin/bash
# Build script for all Docker images

set -e

# Configuration
REGISTRY="${DOCKER_REGISTRY:-gcr.io/trading-platform}"
VERSION="${VERSION:-latest}"

echo "Building Docker images for trading platform..."
echo "Registry: $REGISTRY"
echo "Version: $VERSION"
echo ""

# Build API Gateway
echo "Building API Gateway..."
docker build -f api_gateway/Dockerfile -t ${REGISTRY}/api-gateway:${VERSION} .
echo "✓ API Gateway built successfully"
echo ""

# Build WebSocket Service
echo "Building WebSocket Service..."
docker build -f websocket_service/Dockerfile -t ${REGISTRY}/websocket-service:${VERSION} .
echo "✓ WebSocket Service built successfully"
echo ""

# Build Strategy Execution Service
echo "Building Strategy Execution Service..."
docker build -f strategy_workers/Dockerfile -t ${REGISTRY}/strategy-service:${VERSION} .
echo "✓ Strategy Execution Service built successfully"
echo ""

# Build Order Processing Service
echo "Building Order Processing Service..."
docker build -f order_processor/Dockerfile -t ${REGISTRY}/order-service:${VERSION} .
echo "✓ Order Processing Service built successfully"
echo ""

# Build Analytics Service
echo "Building Analytics Service..."
docker build -f analytics_service/Dockerfile -t ${REGISTRY}/analytics-service:${VERSION} .
echo "✓ Analytics Service built successfully"
echo ""

echo "All images built successfully!"
echo ""
echo "To push images to registry, run:"
echo "  docker push ${REGISTRY}/api-gateway:${VERSION}"
echo "  docker push ${REGISTRY}/websocket-service:${VERSION}"
echo "  docker push ${REGISTRY}/strategy-service:${VERSION}"
echo "  docker push ${REGISTRY}/order-service:${VERSION}"
echo "  docker push ${REGISTRY}/analytics-service:${VERSION}"
