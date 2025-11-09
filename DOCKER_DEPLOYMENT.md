# Docker Deployment Guide

This guide explains how to build and deploy the trading platform using Docker containers.

## Architecture

The platform consists of 5 microservices:

1. **API Gateway** (Port 8080) - Main REST API for all operations
2. **WebSocket Service** (Port 8081) - Real-time bidirectional communication
3. **Strategy Execution Service** - Background service for executing trading strategies
4. **Order Processing Service** - Background service for order routing and execution
5. **Analytics Service** (Port 8082) - Analytics and reporting endpoints

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 20GB disk space

## Building Images

### Local Development Build

```bash
# Build all images locally
./build-images.sh
```

### Custom Registry Build

```bash
# Set your registry
export DOCKER_REGISTRY=gcr.io/your-project-id
export VERSION=v1.0.0

# Build with custom registry
./build-images.sh
```

## Multi-Stage Build Benefits

All Dockerfiles use multi-stage builds to:
- Minimize final image size (50-70% reduction)
- Separate build dependencies from runtime dependencies
- Improve security by reducing attack surface
- Speed up deployment with smaller images

## Running Services

### Development Environment

Use the standard docker-compose for local development:

```bash
docker-compose up -d
```

### Production Environment

Use the production docker-compose with environment variables:

```bash
# Create .env file with required variables
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/trading_platform
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# JWT
JWT_SECRET_KEY=your_jwt_secret_key

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=trading-platform
INFLUXDB_BUCKET=market-data
INFLUXDB_ADMIN_PASSWORD=your_influxdb_password

# Docker Registry (optional)
DOCKER_REGISTRY=gcr.io/your-project-id
VERSION=latest
```

## Service Details

### API Gateway
- **Image**: `api-gateway:latest`
- **Port**: 8080
- **Resources**: 2 CPU, 2GB RAM
- **Dependencies**: PostgreSQL, Redis
- **Health Check**: `GET /health`

### WebSocket Service
- **Image**: `websocket-service:latest`
- **Port**: 8081
- **Resources**: 2 CPU, 2GB RAM
- **Dependencies**: Redis
- **Health Check**: `GET /health`
- **Worker**: Eventlet (for WebSocket support)

### Strategy Execution Service
- **Image**: `strategy-service:latest`
- **Resources**: 2 CPU, 2GB RAM
- **Dependencies**: PostgreSQL, Redis, InfluxDB
- **Type**: Background worker

### Order Processing Service
- **Image**: `order-service:latest`
- **Resources**: 1 CPU, 1GB RAM
- **Dependencies**: PostgreSQL, Redis
- **Type**: Background worker

### Analytics Service
- **Image**: `analytics-service:latest`
- **Port**: 8082
- **Resources**: 1 CPU, 1GB RAM
- **Dependencies**: PostgreSQL, Redis, InfluxDB
- **Health Check**: `GET /health`

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-gateway

# Last 100 lines
docker-compose logs --tail=100 websocket-service
```

### Check Service Health

```bash
# API Gateway
curl http://localhost:8080/health

# WebSocket Service
curl http://localhost:8081/health

# Analytics Service
curl http://localhost:8082/health
```

### Resource Usage

```bash
# View resource usage
docker stats

# View specific service
docker stats trading_api_gateway
```

## Scaling

### Scale Specific Services

```bash
# Scale API Gateway to 3 instances
docker-compose -f docker-compose.prod.yml up -d --scale api-gateway=3

# Scale WebSocket Service to 2 instances
docker-compose -f docker-compose.prod.yml up -d --scale websocket-service=2
```

### Resource Limits

Resource limits are defined in `docker-compose.prod.yml`:
- **Limits**: Maximum resources a container can use
- **Reservations**: Guaranteed minimum resources

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs service-name

# Check container status
docker ps -a

# Inspect container
docker inspect container-name
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test database connection
docker-compose exec postgres psql -U postgres -d trading_platform
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
# Or adjust resource limits in docker-compose.prod.yml
```

## Cleanup

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Remove Images

```bash
# Remove all trading platform images
docker rmi $(docker images | grep 'trading-platform' | awk '{print $3}')
```

## Security Best Practices

1. **Non-root User**: All containers run as non-root user (uid 1000)
2. **Secrets Management**: Use environment variables or Docker secrets
3. **Network Isolation**: Services communicate on internal Docker network
4. **Health Checks**: All services have health checks configured
5. **Resource Limits**: Prevent resource exhaustion with limits
6. **Minimal Images**: Multi-stage builds reduce attack surface

## Next Steps

- Configure Cloud Run deployment (see Task 14.3)
- Set up CI/CD pipeline (see Task 14.7)
- Configure monitoring and logging (see Task 14.6)
- Perform load testing (see Task 14.8)
