# Secret Manager Guide

This guide explains how to manage secrets using Google Secret Manager for the trading platform.

## Overview

Google Secret Manager provides secure storage and management of sensitive configuration data such as:
- Database credentials
- API keys
- JWT signing keys
- Broker credentials

## Secrets Configuration

### Managed Secrets

| Secret Name | Description | Rotation Period | Auto-Generated |
|-------------|-------------|-----------------|----------------|
| `database-url` | PostgreSQL connection string | 90 days | Yes |
| `database-replica-url` | Read replica connection string | 90 days | Yes |
| `redis-host` | Redis instance host | N/A | Yes |
| `jwt-secret-key` | JWT signing key | 90 days | Yes |
| `influxdb-url` | InfluxDB connection URL | N/A | No |
| `influxdb-token` | InfluxDB auth token | 90 days | No |
| `angel-one-api-key` | Angel One broker credentials | 90 days | No |

### Secret Rotation

Secrets are configured with automatic rotation reminders:
- **Rotation Period**: 90 days
- **Notification**: 7 days before rotation due
- **Process**: Manual rotation required for external credentials

## Setup

### 1. Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
```

### 2. Create Secrets via Terraform

```bash
cd infrastructure/terraform
terraform apply -target=google_secret_manager_secret.database_url
terraform apply -target=google_secret_manager_secret.redis_host
terraform apply -target=google_secret_manager_secret.jwt_secret_key
terraform apply -target=google_secret_manager_secret.influxdb_url
terraform apply -target=google_secret_manager_secret.influxdb_token
terraform apply -target=google_secret_manager_secret.angel_one_api_key
```

### 3. Update Broker Credentials

```bash
cd infrastructure/scripts
chmod +x manage-secrets.sh

# Interactive setup
./manage-secrets.sh setup-broker
```

## Management

### List All Secrets

```bash
./manage-secrets.sh list
```

### Get Secret Value

```bash
./manage-secrets.sh get database-url
```

### Update Secret

```bash
./manage-secrets.sh update jwt-secret-key "new-secret-value"
```

### Rotate Secret

```bash
# Rotate and disable old versions
./manage-secrets.sh rotate jwt-secret-key "new-rotated-value"
```

### Grant Access

```bash
./manage-secrets.sh grant-access database-url \
  trading-platform-sa@PROJECT_ID.iam.gserviceaccount.com
```

### Delete Secret

```bash
./manage-secrets.sh delete old-secret-name
```

## Access Control

### Service Account Permissions

The `trading-platform-sa` service account has `secretAccessor` role for all secrets:

```bash
# Grant access to new secret
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:trading-platform-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Audit Logging

All secret access is logged:

```bash
# View secret access logs
gcloud logging read "resource.type=secretmanager.googleapis.com/Secret" \
  --limit=50 \
  --format=json
```

## Usage in Cloud Run

### Environment Variable Reference

In Cloud Run YAML files:

```yaml
env:
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: database-url
      key: latest
```

### Accessing in Application

Secrets are automatically injected as environment variables:

```python
import os

database_url = os.getenv('DATABASE_URL')
redis_host = os.getenv('REDIS_HOST')
jwt_secret = os.getenv('JWT_SECRET_KEY')
```

## Security Best Practices

### 1. Principle of Least Privilege

- Grant access only to services that need it
- Use separate service accounts for different services
- Regularly audit IAM bindings

### 2. Secret Rotation

```bash
# Rotate JWT secret every 90 days
NEW_JWT_SECRET=$(openssl rand -base64 64)
./manage-secrets.sh rotate jwt-secret-key "$NEW_JWT_SECRET"

# Restart services to pick up new secret
gcloud run services update api-gateway --region=asia-south1
```

### 3. Version Management

```bash
# List all versions
gcloud secrets versions list database-url

# Access specific version
gcloud secrets versions access 2 --secret=database-url

# Disable old version
gcloud secrets versions disable 1 --secret=database-url

# Destroy version (permanent)
gcloud secrets versions destroy 1 --secret=database-url
```

### 4. Monitoring

```bash
# Set up alerts for secret access
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Secret Access Alert" \
  --condition-display-name="High secret access rate" \
  --condition-threshold-value=100 \
  --condition-threshold-duration=60s
```

## Broker Credentials Format

### Angel One Credentials

```json
{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "client_code": "your_client_code",
  "password": "your_password",
  "totp_secret": "your_totp_secret"
}
```

Store as JSON string in `angel-one-api-key` secret.

### Adding New Broker

```bash
# Create secret for new broker
./manage-secrets.sh create upstox-api-key '{
  "api_key": "...",
  "api_secret": "..."
}'

# Grant access
./manage-secrets.sh grant-access upstox-api-key \
  trading-platform-sa@PROJECT_ID.iam.gserviceaccount.com
```

## Backup and Recovery

### Export Secrets (for backup)

```bash
# Export all secrets (encrypted)
for SECRET in $(gcloud secrets list --format="value(name)"); do
  echo "Exporting $SECRET..."
  gcloud secrets versions access latest --secret=$SECRET > "backup_${SECRET}.txt"
done

# Encrypt backup
tar czf secrets-backup.tar.gz backup_*.txt
gpg --symmetric --cipher-algo AES256 secrets-backup.tar.gz
rm backup_*.txt secrets-backup.tar.gz
```

### Restore Secrets

```bash
# Decrypt backup
gpg --decrypt secrets-backup.tar.gz.gpg > secrets-backup.tar.gz
tar xzf secrets-backup.tar.gz

# Restore secrets
for FILE in backup_*.txt; do
  SECRET_NAME=$(echo $FILE | sed 's/backup_//' | sed 's/.txt//')
  echo "Restoring $SECRET_NAME..."
  cat $FILE | gcloud secrets versions add $SECRET_NAME --data-file=-
done
```

## Cost

### Pricing

- **Secret Storage**: $0.06 per secret per month
- **Access Operations**: $0.03 per 10,000 operations
- **Estimated Monthly Cost**: ~$1-2 for 10 secrets with moderate access

### Cost Optimization

- Delete unused secrets
- Use secret versions efficiently
- Cache secrets in application when possible

## Troubleshooting

### Permission Denied

```bash
# Check IAM bindings
gcloud secrets get-iam-policy SECRET_NAME

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### Secret Not Found

```bash
# Verify secret exists
gcloud secrets describe SECRET_NAME

# Check project
gcloud config get-value project
```

### Version Issues

```bash
# List versions
gcloud secrets versions list SECRET_NAME

# Check version state
gcloud secrets versions describe VERSION --secret=SECRET_NAME
```

## Next Steps

- Configure Load Balancer (Task 14.5)
- Set up monitoring and logging (Task 14.6)
- Implement CI/CD pipeline (Task 14.7)
