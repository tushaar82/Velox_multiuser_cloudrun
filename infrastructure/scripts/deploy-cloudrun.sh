#!/bin/bash
# Deploy all Cloud Run services

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"asia-south1"}
REGISTRY="gcr.io/${PROJECT_ID}"

echo "Deploying Cloud Run services to project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Function to replace PROJECT_ID in YAML files
replace_project_id() {
    local file=$1
    sed "s/PROJECT_ID/${PROJECT_ID}/g" "$file" > "${file}.tmp"
    mv "${file}.tmp" "$file"
}

# Deploy API Gateway
echo "Deploying API Gateway..."
replace_project_id infrastructure/cloudrun/api-gateway.yaml
gcloud run services replace infrastructure/cloudrun/api-gateway.yaml \
    --region=$REGION \
    --platform=managed
echo "✓ API Gateway deployed"
echo ""

# Deploy WebSocket Service
echo "Deploying WebSocket Service..."
replace_project_id infrastructure/cloudrun/websocket-service.yaml
gcloud run services replace infrastructure/cloudrun/websocket-service.yaml \
    --region=$REGION \
    --platform=managed
echo "✓ WebSocket Service deployed"
echo ""

# Deploy Strategy Service
echo "Deploying Strategy Service..."
replace_project_id infrastructure/cloudrun/strategy-service.yaml
gcloud run services replace infrastructure/cloudrun/strategy-service.yaml \
    --region=$REGION \
    --platform=managed
echo "✓ Strategy Service deployed"
echo ""

# Deploy Order Service
echo "Deploying Order Service..."
replace_project_id infrastructure/cloudrun/order-service.yaml
gcloud run services replace infrastructure/cloudrun/order-service.yaml \
    --region=$REGION \
    --platform=managed
echo "✓ Order Service deployed"
echo ""

# Deploy Analytics Service
echo "Deploying Analytics Service..."
replace_project_id infrastructure/cloudrun/analytics-service.yaml
gcloud run services replace infrastructure/cloudrun/analytics-service.yaml \
    --region=$REGION \
    --platform=managed
echo "✓ Analytics Service deployed"
echo ""

echo "All services deployed successfully!"
echo ""
echo "Service URLs:"
gcloud run services list --region=$REGION --platform=managed --format="table(SERVICE,URL)"
