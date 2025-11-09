# Monitoring and Logging Guide

This guide explains the monitoring and logging setup for the trading platform.

## Overview

The platform uses Google Cloud Monitoring and Logging with:
- **Structured JSON Logging**: All logs in JSON format for easy parsing
- **Custom Metrics**: Trading-specific metrics (orders/sec, strategy errors)
- **Alert Policies**: Automated alerts for critical issues
- **Dashboards**: Real-time visualization of system health
- **Log Retention**: 90-day retention with automatic archival

## Architecture

```
Application Logs
    ↓
[Cloud Logging]
    ├── Real-time Analysis
    ├── Custom Metrics Extraction
    ├── Alert Evaluation
    └── Long-term Storage (Cloud Storage)

Metrics
    ↓
[Cloud Monitoring]
    ├── Dashboards
    ├── Alert Policies
    └── Notification Channels
```

## Setup

### 1. Configure Alert Email

```bash
# Update terraform.tfvars
echo 'alert_email = "alerts@example.com"' >> infrastructure/terraform/terraform.tfvars

# Optional: Add Slack webhook
echo 'slack_webhook_url = "https://hooks.slack.com/services/..."' >> infrastructure/terraform/terraform.tfvars
```

### 2. Deploy Monitoring Configuration

```bash
cd infrastructure/terraform
terraform apply -target=google_monitoring_notification_channel.email
terraform apply -target=google_monitoring_alert_policy.high_error_rate
terraform apply
```

### 3. Access Dashboard

```bash
# Get dashboard URL
terraform output monitoring_dashboard_url

# Or access via Cloud Console
# Monitoring → Dashboards → Trading Platform Dashboard
```

## Alert Policies

### Configured Alerts

| Alert | Condition | Threshold | Duration | Action |
|-------|-----------|-----------|----------|--------|
| High Error Rate | 5xx errors | > 5% | 5 min | Email + Slack |
| High Latency | 95th percentile | > 2s | 5 min | Email + Slack |
| High CPU | CPU utilization | > 80% | 5 min | Email + Slack |
| High Memory | Memory utilization | > 90% | 5 min | Email + Slack |
| DB Connections | Active connections | > 450 | 5 min | Email + Slack |
| Redis Memory | Memory usage | > 90% | 5 min | Email + Slack |

### Managing Alerts

```bash
# List all alert policies
gcloud alpha monitoring policies list

# Update alert threshold
gcloud alpha monitoring policies update POLICY_ID \
  --condition-threshold-value=0.10

# Disable alert
gcloud alpha monitoring policies update POLICY_ID \
  --enabled=false

# Delete alert
gcloud alpha monitoring policies delete POLICY_ID
```

## Custom Metrics

### Trading Metrics

1. **Orders Per Second**
   - Metric: `logging.googleapis.com/user/trading/orders_per_second`
   - Labels: `trading_mode` (paper/live)
   - Type: DELTA

2. **Strategy Errors**
   - Metric: `logging.googleapis.com/user/trading/strategy_errors`
   - Labels: `strategy_id`
   - Type: DELTA

### Logging Custom Events

```python
import logging
from shared.utils.logging_config import get_logger, LogContext

logger = get_logger(__name__)

# Log order submission
with LogContext(logger, event='order_submitted', trading_mode='live', order_id='123'):
    logger.info('Order submitted successfully')

# Log strategy error
with LogContext(logger, event='strategy_error', strategy_id='ma-crossover'):
    logger.error('Strategy execution failed', exc_info=True)
```

### Creating Custom Metrics

```bash
# Create new log-based metric
gcloud logging metrics create METRIC_NAME \
  --description="Description" \
  --log-filter='resource.type="cloud_run_revision" AND jsonPayload.event="EVENT_NAME"'
```

## Structured Logging

### JSON Log Format

All logs are output in JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "severity": "INFO",
  "logger": "api_gateway.order_service",
  "message": "Order submitted successfully",
  "module": "order_service",
  "function": "submit_order",
  "line": 145,
  "event": "order_submitted",
  "user_id": "user123",
  "account_id": "acc456",
  "order_id": "ord789",
  "trading_mode": "live"
}
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical messages for severe failures

### Best Practices

1. **Use Structured Fields**: Add context with extra fields
2. **Consistent Event Names**: Use standard event names across services
3. **Include IDs**: Always log user_id, account_id, order_id when available
4. **Avoid PII**: Don't log sensitive personal information
5. **Use Appropriate Levels**: Choose correct severity level

## Viewing Logs

### Cloud Console

```
Logging → Logs Explorer
```

### gcloud CLI

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=50 \
  --format=json

# Filter by service
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=api-gateway" \
  --limit=50

# Filter by severity
gcloud logging read "severity>=ERROR" \
  --limit=50

# Filter by custom field
gcloud logging read "jsonPayload.event=order_submitted" \
  --limit=50

# Filter by time range
gcloud logging read "timestamp>=\"2024-01-15T00:00:00Z\"" \
  --limit=50

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision"
```

### Advanced Queries

```bash
# Orders in last hour
gcloud logging read '
  resource.type="cloud_run_revision"
  AND jsonPayload.event="order_submitted"
  AND timestamp>="'$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)'"
' --format=json

# Strategy errors by strategy_id
gcloud logging read '
  jsonPayload.event="strategy_error"
' --format="table(timestamp, jsonPayload.strategy_id, jsonPayload.message)"

# High latency requests
gcloud logging read '
  resource.type="cloud_run_revision"
  AND httpRequest.latency>"2s"
' --limit=50
```

## Dashboards

### Main Dashboard Widgets

1. **Request Rate**: Requests per second across all services
2. **Error Rate**: 5xx errors per second
3. **Latency**: 95th percentile response time
4. **CPU Utilization**: CPU usage by service
5. **Memory Utilization**: Memory usage by service
6. **Database Connections**: Active database connections
7. **Redis Memory**: Redis memory usage
8. **Orders Per Second**: Trading activity

### Creating Custom Dashboards

```bash
# Export existing dashboard
gcloud monitoring dashboards describe DASHBOARD_ID \
  --format=json > dashboard.json

# Create new dashboard
gcloud monitoring dashboards create --config-from-file=dashboard.json

# Update dashboard
gcloud monitoring dashboards update DASHBOARD_ID \
  --config-from-file=dashboard.json
```

### Dashboard JSON Example

```json
{
  "displayName": "Custom Trading Dashboard",
  "gridLayout": {
    "widgets": [
      {
        "title": "Active Users",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"logging.googleapis.com/user/trading/active_users\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_MEAN"
                }
              }
            }
          }]
        }
      }
    ]
  }
}
```

## Log Retention

### Retention Policy

- **Cloud Logging**: 30 days (default)
- **Cloud Storage**: 90 days (then deleted)
- **Nearline Storage**: After 30 days (cost optimization)

### Managing Retention

```bash
# View log sink
gcloud logging sinks describe trading-platform-logs-sink

# Update retention
gsutil lifecycle set lifecycle.json gs://BUCKET_NAME

# lifecycle.json example:
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      }
    ]
  }
}
```

## Cost Optimization

### Estimated Costs

- **Cloud Logging**: $0.50/GB ingested (first 50GB free)
- **Cloud Monitoring**: $0.2580 per million data points
- **Cloud Storage**: $0.020/GB/month (Standard), $0.010/GB/month (Nearline)
- **Estimated Total**: $50-100/month (depending on volume)

### Cost Reduction Tips

1. **Filter Logs**: Only log important events
2. **Sampling**: Use log sampling for high-volume logs
3. **Retention**: Reduce retention period if not needed
4. **Exclusion Filters**: Exclude noisy logs

```bash
# Create exclusion filter
gcloud logging sinks update trading-platform-logs-sink \
  --add-exclusion=name=exclude-health-checks,filter='httpRequest.requestUrl=~"/health"'
```

## Monitoring Best Practices

### 1. Set Up Alerts Early

Configure alerts before issues occur:
- Error rate thresholds
- Latency thresholds
- Resource utilization limits

### 2. Use Dashboards

Create dashboards for:
- System health overview
- Trading activity monitoring
- Performance metrics
- Business metrics

### 3. Regular Review

- Review alerts weekly
- Adjust thresholds based on patterns
- Archive old logs
- Update dashboards as needed

### 4. Incident Response

When alert fires:
1. Check dashboard for context
2. View recent logs
3. Identify root cause
4. Take corrective action
5. Document incident

## Troubleshooting

### No Logs Appearing

```bash
# Check log router
gcloud logging sinks list

# Verify service account permissions
gcloud projects get-iam-policy PROJECT_ID

# Test logging
gcloud logging write test-log "Test message" --severity=INFO
```

### Alerts Not Firing

```bash
# Check alert policy
gcloud alpha monitoring policies describe POLICY_ID

# Verify notification channel
gcloud alpha monitoring channels describe CHANNEL_ID

# Test notification
gcloud alpha monitoring channels verify CHANNEL_ID
```

### High Logging Costs

```bash
# View log volume by resource
gcloud logging read "timestamp>=\"$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)\"" \
  --format="table(resource.type)" \
  | sort | uniq -c | sort -rn

# Add exclusion filters for noisy logs
gcloud logging sinks update trading-platform-logs-sink \
  --add-exclusion=name=exclude-debug,filter='severity<WARNING'
```

## Next Steps

- Implement CI/CD pipeline (Task 14.7)
- Perform load testing (Task 14.8)
- Set up uptime checks
- Configure SLO monitoring
