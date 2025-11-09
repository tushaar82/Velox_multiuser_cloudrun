# Load Testing Guide

This guide explains how to perform load testing and optimization for the trading platform.

## Overview

Load testing validates that the platform can handle:
- **500 concurrent users** for API requests
- **2500+ WebSocket connections** for real-time updates
- **Sub-2-second response times** at 95th percentile
- **Zero errors** under normal load

## Tools

- **Artillery**: HTTP and WebSocket load testing
- **Apache Bench**: Simple HTTP benchmarking
- **Cloud Monitoring**: Real-time metrics during tests

## Setup

### Install Artillery

```bash
# Install globally
npm install -g artillery

# Verify installation
artillery --version
```

### Prepare Test Environment

```bash
# Create results directory
mkdir -p load-tests/results

# Make scripts executable
chmod +x load-tests/*.sh

# Set target URL
export TARGET_URL=https://staging.example.com
```

## Running Tests

### API Load Tests

Tests 500 concurrent users with realistic trading scenarios:

```bash
cd load-tests
./run-tests.sh api
```

**Test Phases**:
1. Warm-up: 10 users/sec for 60s
2. Ramp-up: 10→100 users/sec over 5 min
3. Sustained: 100 users/sec for 10 min
4. Peak: 100→500 users/sec over 5 min
5. Peak sustained: 500 users/sec for 10 min
6. Ramp-down: 500→0 users/sec over 3 min

**Scenarios**:
- Authentication Flow (20%)
- View Dashboard (30%)
- Place Order (25%)
- View Analytics (15%)
- WebSocket Connection (10%)

### WebSocket Load Tests

Tests 2500+ concurrent WebSocket connections:

```bash
cd load-tests
./run-tests.sh websocket
```

**Test Phases**:
1. Ramp-up: 10→50 connections/sec over 5 min (1000 total)
2. Sustained: 50 connections/sec for 10 min
3. Peak: 50→125 connections/sec over 5 min (2500 total)
4. Peak sustained: 125 connections/sec for 15 min
5. Ramp-down: 125→0 connections/sec over 3 min

### All Tests

Run both API and WebSocket tests:

```bash
cd load-tests
./run-tests.sh all
```

## Analyzing Results

### Generate Report

```bash
cd load-tests
./analyze-results.sh
```

**Output**:
- HTML report with charts
- Performance summary
- Benchmark validation

### Key Metrics

| Metric | Target | Acceptable |
|--------|--------|------------|
| Response Time (p95) | < 1s | < 2s |
| Response Time (p99) | < 2s | < 5s |
| Error Rate | 0% | < 1% |
| Requests/sec | 500+ | 300+ |
| WebSocket Connections | 2500+ | 2000+ |
| CPU Utilization | < 70% | < 80% |
| Memory Utilization | < 80% | < 90% |

### View Metrics in Cloud Console

```bash
# Open monitoring dashboard
gcloud monitoring dashboards list

# View real-time metrics during test
# Monitoring → Dashboards → Trading Platform Dashboard
```

## Performance Benchmarks

### Expected Results (500 concurrent users)

```
Request Rate: 500-600 req/sec
Response Time:
  Min: 50ms
  Median: 200ms
  p95: 800ms
  p99: 1500ms
  Max: 3000ms

Status Codes:
  200: 95%
  201: 4%
  4xx: 0.5%
  5xx: 0.5%

Errors: < 1%
```

### Expected Results (2500 WebSocket connections)

```
Concurrent Connections: 2500+
Connection Time: < 500ms
Message Latency: < 100ms
Disconnection Rate: < 0.1%
```

## Optimization

### Identified Bottlenecks

Common bottlenecks and solutions:

1. **High Latency**
   - Increase min instances
   - Optimize database queries
   - Add caching layer
   - Use read replicas

2. **High CPU**
   - Increase CPU allocation
   - Optimize algorithms
   - Use async processing
   - Scale horizontally

3. **High Memory**
   - Increase memory allocation
   - Fix memory leaks
   - Optimize data structures
   - Use pagination

4. **Database Connections**
   - Use connection pooling (PgBouncer)
   - Optimize query patterns
   - Add read replicas
   - Cache frequently accessed data

5. **WebSocket Issues**
   - Enable session affinity
   - Increase timeout
   - Optimize message size
   - Use Redis pub/sub

### Optimization Steps

#### 1. Increase Min Instances

```bash
# Reduce cold starts
gcloud run services update api-gateway \
  --min-instances=5 \
  --region=asia-south1
```

#### 2. Optimize Resource Allocation

```bash
# Increase CPU and memory
gcloud run services update api-gateway \
  --cpu=4 \
  --memory=4Gi \
  --region=asia-south1
```

#### 3. Enable Connection Pooling

```bash
# Deploy PgBouncer
cd infrastructure/scripts
./setup-pgbouncer.sh

# Update DATABASE_URL to use PgBouncer
```

#### 4. Add Caching

```python
# Add Redis caching for frequently accessed data
from redis import Redis

redis_client = Redis(host='redis-host', port=6379)

def get_user_data(user_id):
    # Check cache first
    cached = redis_client.get(f'user:{user_id}')
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    user = db.query(User).filter_by(id=user_id).first()
    
    # Cache for 5 minutes
    redis_client.setex(f'user:{user_id}', 300, json.dumps(user.to_dict()))
    
    return user
```

#### 5. Optimize Database Queries

```python
# Use eager loading to reduce N+1 queries
from sqlalchemy.orm import joinedload

# Bad: N+1 queries
users = db.query(User).all()
for user in users:
    print(user.account.name)  # Separate query for each user

# Good: Single query with join
users = db.query(User).options(joinedload(User.account)).all()
for user in users:
    print(user.account.name)  # No additional queries
```

#### 6. Add Indexes

```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_orders_account_id ON orders(account_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_positions_account_id ON positions(account_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
```

## Continuous Testing

### Automated Load Tests

Run load tests automatically after deployment:

```yaml
# Add to cloudbuild.yaml
- name: 'node:18'
  id: 'load-tests'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      npm install -g artillery
      cd load-tests
      ./run-tests.sh api
      ./analyze-results.sh
  waitFor: ['deploy-staging']
```

### Performance Monitoring

Set up alerts for performance degradation:

```bash
# Create alert for high latency
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Latency Alert" \
  --condition-threshold-value=2000 \
  --condition-threshold-duration=300s \
  --condition-display-name="p95 latency > 2s"
```

## Troubleshooting

### High Error Rate

```bash
# Check error logs
gcloud logging read "severity>=ERROR" \
  --limit=50 \
  --format=json

# Common causes:
# 1. Database connection pool exhausted
# 2. Rate limiting triggered
# 3. Memory exhaustion
# 4. Timeout errors
```

### Slow Response Times

```bash
# Check slow queries
gcloud sql operations list \
  --instance=trading-platform-db-prod \
  --filter="operationType:QUERY"

# Profile slow endpoints
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"' \
  --format=json
```

### WebSocket Connection Issues

```bash
# Check WebSocket logs
gcloud run services logs read websocket-service \
  --region=asia-south1 \
  --limit=100

# Common causes:
# 1. Session affinity not enabled
# 2. Timeout too short
# 3. Redis pub/sub issues
# 4. Memory exhaustion
```

## Best Practices

1. **Test Regularly**: Run load tests after major changes
2. **Monitor Metrics**: Watch metrics during tests
3. **Gradual Scaling**: Ramp up load gradually
4. **Realistic Scenarios**: Use realistic user behavior
5. **Test Edge Cases**: Test error scenarios
6. **Document Results**: Keep history of test results
7. **Optimize Iteratively**: Make one change at a time

## Cost Considerations

Load testing can incur costs:

- **Cloud Run**: Increased instance hours
- **Database**: Higher CPU and memory usage
- **Network**: Data transfer costs
- **Monitoring**: Increased metrics volume

**Estimated Cost**: $10-20 per test run

**Cost Reduction**:
- Test during off-peak hours
- Use staging environment
- Limit test duration
- Clean up after tests

## Next Steps

- Set up continuous performance monitoring
- Implement automated performance regression tests
- Create performance budgets
- Document optimization strategies
- Train team on performance best practices
