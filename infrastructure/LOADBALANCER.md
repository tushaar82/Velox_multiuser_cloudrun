# Load Balancer Configuration Guide

This guide explains the Cloud Load Balancer setup for the trading platform.

## Overview

The platform uses Google Cloud Load Balancer (HTTPS) with the following features:
- **SSL/TLS Termination**: Managed SSL certificates with automatic renewal
- **HTTP to HTTPS Redirect**: Automatic redirect from HTTP to HTTPS
- **Path-based Routing**: Route requests to appropriate backend services
- **Session Affinity**: Sticky sessions for WebSocket connections
- **Cloud Armor**: DDoS protection and rate limiting
- **Health Checks**: Automatic backend health monitoring

## Architecture

```
Internet
    ↓
[Cloud Load Balancer]
    ├── HTTPS (443) → HTTPS Proxy → URL Map
    └── HTTP (80) → HTTP Proxy → Redirect to HTTPS
                                      ↓
                            ┌─────────┴─────────┐
                            │                   │
                    [Path Matcher]      [Security Policy]
                            │                   │
        ┌───────────────────┼───────────────────┼────────────┐
        │                   │                   │            │
    /api/*            /ws/*,/socket.io/*   /api/analytics/*  │
        │                   │                   │            │
        ↓                   ↓                   ↓            ↓
  [API Gateway]      [WebSocket Service]  [Analytics]  [Default]
```

## Routing Rules

| Path Pattern | Backend Service | Timeout | Session Affinity |
|--------------|----------------|---------|------------------|
| `/api/*` | API Gateway | 300s | None |
| `/ws/*`, `/socket.io/*` | WebSocket Service | 3600s | CLIENT_IP |
| `/api/analytics/*` | Analytics Service | 600s | None |
| Default | API Gateway | 300s | None |

## Setup

### 1. Configure Domain

```bash
# Set your domain name
export DOMAIN_NAME=trading.example.com

# Update terraform.tfvars
echo 'domain_name = "trading.example.com"' >> infrastructure/terraform/terraform.tfvars
```

### 2. Deploy Load Balancer

```bash
cd infrastructure/terraform
terraform apply -target=google_compute_global_address.lb_ip
terraform apply -target=google_compute_managed_ssl_certificate.lb_cert
terraform apply
```

### 3. Configure DNS

```bash
# Get load balancer IP
LB_IP=$(terraform output -raw load_balancer_ip)

echo "Configure DNS A record:"
echo "  Name: $DOMAIN_NAME"
echo "  Type: A"
echo "  Value: $LB_IP"
```

Add DNS A record in your domain registrar:
- **Name**: `trading` (or `@` for root domain)
- **Type**: A
- **Value**: Load balancer IP address
- **TTL**: 300

### 4. Wait for SSL Certificate

```bash
# Check certificate status
gcloud compute ssl-certificates describe trading-platform-ssl-cert \
  --global \
  --format="value(managed.status)"

# Wait for ACTIVE status (can take 15-60 minutes)
while [ "$(gcloud compute ssl-certificates describe trading-platform-ssl-cert --global --format='value(managed.status)')" != "ACTIVE" ]; do
  echo "Waiting for SSL certificate provisioning..."
  sleep 30
done

echo "SSL certificate is active!"
```

## Security Configuration

### Cloud Armor Rules

1. **Rate Limiting**
   - Limit: 1000 requests per minute per IP
   - Action: Ban for 10 minutes if exceeded
   - Response: HTTP 429 (Too Many Requests)

2. **SQL Injection Protection**
   - Blocks common SQL injection patterns
   - Response: HTTP 403 (Forbidden)

3. **XSS Protection**
   - Blocks cross-site scripting attempts
   - Response: HTTP 403 (Forbidden)

### Custom Rules

```bash
# Add custom rule to block specific IPs
gcloud compute security-policies rules create 3000 \
  --security-policy=trading-platform-security-policy \
  --action=deny-403 \
  --src-ip-ranges=1.2.3.4/32 \
  --description="Block malicious IP"

# Add geo-restriction (example: allow only India)
gcloud compute security-policies rules create 3001 \
  --security-policy=trading-platform-security-policy \
  --action=deny-403 \
  --expression="origin.region_code != 'IN'" \
  --description="Allow only India traffic"
```

## Health Checks

### Configuration

| Service | Path | Interval | Timeout | Healthy Threshold | Unhealthy Threshold |
|---------|------|----------|---------|-------------------|---------------------|
| API Gateway | `/health` | 10s | 5s | 2 | 3 |
| WebSocket | `/health` | 10s | 5s | 2 | 3 |
| Analytics | `/health` | 10s | 5s | 2 | 3 |

### Monitor Health

```bash
# Check backend health
gcloud compute backend-services get-health api-gateway-backend \
  --global

# View health check logs
gcloud logging read "resource.type=http_load_balancer" \
  --limit=50 \
  --format=json
```

## Monitoring

### View Metrics

```bash
# Request count
gcloud monitoring time-series list \
  --filter='resource.type="https_lb_rule" AND metric.type="loadbalancing.googleapis.com/https/request_count"' \
  --format=json

# Latency
gcloud monitoring time-series list \
  --filter='resource.type="https_lb_rule" AND metric.type="loadbalancing.googleapis.com/https/total_latencies"' \
  --format=json
```

### Cloud Console

Access detailed metrics in Cloud Console:
- **Network Services** → **Load Balancing**
- View request rate, latency, error rate
- Backend health status
- SSL certificate status

## Testing

### Test HTTPS

```bash
# Test API Gateway
curl -I https://trading.example.com/health

# Test WebSocket
curl -I https://trading.example.com/ws/health

# Test Analytics
curl -I https://trading.example.com/api/analytics/health
```

### Test HTTP Redirect

```bash
# Should redirect to HTTPS
curl -I http://trading.example.com/health
```

### Test Rate Limiting

```bash
# Send 1100 requests in 60 seconds
for i in {1..1100}; do
  curl -s https://trading.example.com/health > /dev/null &
done
wait

# Should receive 429 after 1000 requests
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run load test
ab -n 10000 -c 100 https://trading.example.com/health

# Results show:
# - Requests per second
# - Time per request
# - Transfer rate
# - Connection times
```

## Troubleshooting

### SSL Certificate Not Provisioning

```bash
# Check certificate status
gcloud compute ssl-certificates describe trading-platform-ssl-cert \
  --global

# Common issues:
# 1. DNS not configured correctly
# 2. Domain not pointing to load balancer IP
# 3. CAA records blocking certificate issuance

# Verify DNS
dig trading.example.com +short

# Should return load balancer IP
```

### 502 Bad Gateway

```bash
# Check backend health
gcloud compute backend-services get-health api-gateway-backend --global

# Check Cloud Run service
gcloud run services describe api-gateway --region=asia-south1

# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

### High Latency

```bash
# Check backend latency
gcloud monitoring time-series list \
  --filter='metric.type="loadbalancing.googleapis.com/https/backend_latencies"'

# Optimize:
# 1. Increase min instances to reduce cold starts
# 2. Enable CDN for static content
# 3. Optimize backend service performance
```

### Rate Limiting Issues

```bash
# View blocked requests
gcloud logging read "resource.type=http_load_balancer AND jsonPayload.enforcedSecurityPolicy.name=trading-platform-security-policy" \
  --limit=50

# Adjust rate limit
gcloud compute security-policies rules update 1000 \
  --security-policy=trading-platform-security-policy \
  --rate-limit-threshold-count=2000
```

## Cost Optimization

### Estimated Costs

- **Load Balancer**: ~$18/month (base)
- **Forwarding Rules**: ~$18/month (2 rules)
- **Data Processing**: ~$0.008/GB
- **Cloud Armor**: ~$5/month (base) + $0.75 per million requests
- **Total**: ~$50-100/month (depending on traffic)

### Cost Reduction Tips

1. **Optimize Data Transfer**: Compress responses, minimize payload size
2. **Cache Static Content**: Use CDN for static assets
3. **Efficient Routing**: Minimize backend hops
4. **Monitor Usage**: Set up billing alerts

## Advanced Configuration

### Enable CDN

```bash
# Enable CDN for static content
gcloud compute backend-services update api-gateway-backend \
  --enable-cdn \
  --global
```

### Custom Headers

```bash
# Add custom headers
gcloud compute url-maps add-header api-gateway-backend \
  --header-name="X-Platform" \
  --header-value="Trading-Platform"
```

### WebSocket Optimization

```bash
# Increase timeout for WebSocket
gcloud compute backend-services update websocket-backend \
  --timeout=7200 \
  --global
```

## Next Steps

- Set up monitoring and logging (Task 14.6)
- Implement CI/CD pipeline (Task 14.7)
- Perform load testing (Task 14.8)
