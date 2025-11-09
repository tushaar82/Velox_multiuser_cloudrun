# Cloud Run Deployment Guide

This guide explains how to deploy the trading platform services to Google Cloud Run.

## Overview

Cloud Run is a fully managed serverless platform that automatically scales containers based on incoming requests. The platform consists of 5 services:

1. **API Gateway** - Main REST API (public)
2. **WebSocket Service** - Real-time communication (public)
3. **Analytics Service** - Analytics endpoints (public)
4. **Strategy Service** - Background strategy execution (internal)
5. **Order Service** - Background order processing (internal)

## Architecture

### Auto-Scaling Configuration

| Service | Min Instances | Max Instances | Concurrency | CPU | Memory |
|---------|--------------|---------------|-------------|-----|--------|
| API Gateway | 2 | 100 | 80 | 2 vCPU | 2 GB |
| WebSocket | 2 | 50 | 50 | 2 vCPU | 2 GB |
| Analytics | 1 | 20 | 40 | 1 vCPU | 1 GB |
| Strategy | 1 | 50 | 10 | 2 vCPU | 2 GB |
| Order | 2 | 50 | 20 | 1 vCPU | 1 GB |

### Network Configuration

- **VPC Connector**: Enables private connectivity to Cloud SQL and Redis
- **Egress**: Private ranges only (no public internet access except through NAT)
- **Ingress**: Public for API Gateway, WebSocket, Analytics; Internal for Strategy and Order services

### Resource Optimization

- **CPU Throttling**: Disabled for all services (always-on CPU)
- **Startup CPU Boost**: Enabled for faster cold starts
- **Execution Environment**: Gen2 for WebSocket (better performance)
- **Session Affinity**: Enabled for WebSocket (sticky sessions)

## Prerequisites

1. **VPC Access Connector**
   ```bash
   # Created via Terraform (see vpc-connector.tf)
   terraform apply -target=google_vpc_access_connector.connector
   ```

2. **Service Account**
   ```bash
   # Create service account for Cloud Run
   gcloud iam service-accounts create trading-platform-sa \
     --display-name="Trading Platform Service Account"
   
   # Grant necessary permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:trading-platform-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:trading-platform-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

3. **Container Images**
   ```bash
   # Build and push images
   ./build-images.sh
   
   # Push to GCR
   docker push gcr.io/$PROJECT_ID/api-gateway:latest
   docker push gcr.io/$PROJECT_ID/websocket-service:latest
   docker push gcr.io/$PROJECT_ID/strategy-service:latest
   docker push gcr.io/$PROJECT_ID/order-service:latest
   docker push gcr.io/$PROJECT_ID/analytics-service:latest
   ```

## Deployment

### Automated Deployment

```bash
# Set environment variables
export PROJECT_ID=your-project-id
export REGION=asia-south1

# Deploy all services
cd infrastructure/scripts
chmod +x deploy-cloudrun.sh
./deploy-cloudrun.sh
```

### Manual Deployment

```bash
# Deploy individual service
gcloud run services replace infrastructure/cloudrun/api-gateway.yaml \
  --region=asia-south1 \
  --platform=managed
```

### Update Deployment

```bash
# Update with new image
gcloud run services update api-gateway \
  --image=gcr.io/$PROJECT_ID/api-gateway:v2.0.0 \
  --region=asia-south1
```

## Configuration

### Environment Variables

All services use Secret Manager for sensitive configuration:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_HOST` - Redis instance host
- `JWT_SECRET_KEY` - JWT signing key
- `INFLUXDB_URL` - InfluxDB connection URL
- `INFLUXDB_TOKEN` - InfluxDB authentication token

### Secrets Management

Secrets are referenced in YAML files:
```yaml
env:
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: database-url
      key: latest
```

See Task 14.4 for Secret Manager setup.

### Health Checks

All HTTP services have health checks configured:
- **Liveness Probe**: Checks if service is alive (every 30s)
- **Startup Probe**: Checks if service has started (every 5s, max 60s)
- **Endpoint**: `GET /health`

## Monitoring

### View Logs

```bash
# Stream logs
gcloud run services logs tail api-gateway --region=asia-south1

# View recent logs
gcloud run services logs read api-gateway \
  --region=asia-south1 \
  --limit=100
```

### View Metrics

```bash
# Service metrics
gcloud run services describe api-gateway \
  --region=asia-south1 \
  --format="value(status.traffic)"

# List revisions
gcloud run revisions list \
  --service=api-gateway \
  --region=asia-south1
```

### Cloud Console

Access detailed metrics in Cloud Console:
- Request count and latency
- Instance count and CPU/memory usage
- Error rates and status codes
- Cold start metrics

## Traffic Management

### Blue-Green Deployment

```bash
# Deploy new revision without traffic
gcloud run deploy api-gateway \
  --image=gcr.io/$PROJECT_ID/api-gateway:v2.0.0 \
  --no-traffic \
  --region=asia-south1

# Test new revision
REVISION_URL=$(gcloud run revisions describe api-gateway-00002 \
  --region=asia-south1 \
  --format="value(status.url)")
curl $REVISION_URL/health

# Gradually shift traffic
gcloud run services update-traffic api-gateway \
  --to-revisions=api-gateway-00002=10 \
  --region=asia-south1

# Complete migration
gcloud run services update-traffic api-gateway \
  --to-latest \
  --region=asia-south1
```

### Rollback

```bash
# Rollback to previous revision
gcloud run services update-traffic api-gateway \
  --to-revisions=api-gateway-00001=100 \
  --region=asia-south1
```

## Scaling

### Manual Scaling

```bash
# Update min/max instances
gcloud run services update api-gateway \
  --min-instances=5 \
  --max-instances=200 \
  --region=asia-south1
```

### Concurrency

```bash
# Update container concurrency
gcloud run services update api-gateway \
  --concurrency=100 \
  --region=asia-south1
```

### Resource Limits

```bash
# Update CPU and memory
gcloud run services update api-gateway \
  --cpu=4 \
  --memory=4Gi \
  --region=asia-south1
```

## Cost Optimization

### Estimated Costs (500 concurrent users)

- **API Gateway**: ~$150/month (2 min instances, avg 10 instances)
- **WebSocket**: ~$100/month (2 min instances, avg 5 instances)
- **Analytics**: ~$30/month (1 min instance, avg 2 instances)
- **Strategy**: ~$50/month (1 min instance, avg 3 instances)
- **Order**: ~$60/month (2 min instances, avg 4 instances)
- **Total**: ~$390/month

### Cost Reduction Tips

1. **Reduce Min Instances**: Set to 0 for non-critical services during off-hours
2. **Optimize Concurrency**: Increase concurrency to reduce instance count
3. **Right-size Resources**: Use smaller CPU/memory for less demanding services
4. **Request Timeout**: Reduce timeout for faster failure detection

## Security

### IAM Permissions

```bash
# Allow unauthenticated access (public services)
gcloud run services add-iam-policy-binding api-gateway \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=asia-south1

# Restrict to authenticated users
gcloud run services add-iam-policy-binding strategy-service \
  --member="serviceAccount:trading-platform-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=asia-south1
```

### Network Security

- Internal services (Strategy, Order) only accessible within VPC
- All services use HTTPS
- VPC connector for private database access
- No public IP addresses for databases

## Troubleshooting

### Service Won't Start

```bash
# Check logs
gcloud run services logs read api-gateway \
  --region=asia-south1 \
  --limit=50

# Check revision status
gcloud run revisions describe api-gateway-00001 \
  --region=asia-south1
```

### High Latency

```bash
# Check cold start metrics
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"'

# Increase min instances to reduce cold starts
gcloud run services update api-gateway \
  --min-instances=5 \
  --region=asia-south1
```

### Out of Memory

```bash
# Check memory usage
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/container/memory/utilizations"'

# Increase memory limit
gcloud run services update api-gateway \
  --memory=4Gi \
  --region=asia-south1
```

## Next Steps

- Set up Secret Manager (Task 14.4)
- Configure Load Balancer (Task 14.5)
- Set up monitoring and logging (Task 14.6)
- Implement CI/CD pipeline (Task 14.7)
