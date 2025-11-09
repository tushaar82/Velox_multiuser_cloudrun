# Infrastructure Setup Guide

This directory contains Terraform configurations and scripts for deploying the trading platform infrastructure on Google Cloud Platform.

## Architecture Overview

### Cloud SQL PostgreSQL
- **Primary Instance**: Regional high-availability instance with automatic failover
- **Read Replica**: Dedicated replica for analytics queries
- **Specifications**: 4 vCPU, 16GB RAM, 100GB SSD
- **Backups**: Daily automated backups with 7-day retention and point-in-time recovery
- **Connection Pooling**: PgBouncer for efficient connection management

### Cloud Memorystore Redis
- **Tier**: Standard HA (High Availability) with automatic failover
- **Memory**: 5GB with LRU eviction policy
- **Persistence**: RDB snapshots every 12 hours
- **Replication**: 1 read replica for high availability

### Network Configuration
- **VPC**: Private network for all resources
- **Private IP**: All database connections use private IPs
- **SSL**: Required for all database connections
- **Service Networking**: VPC peering for Cloud SQL

## Prerequisites

1. **Google Cloud SDK**
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Terraform**
   ```bash
   # Install Terraform
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

3. **GCP Project Setup**
   ```bash
   # Set project
   export PROJECT_ID=your-project-id
   gcloud config set project $PROJECT_ID
   
   # Enable required APIs
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable redis.googleapis.com
   gcloud services enable servicenetworking.googleapis.com
   gcloud services enable compute.googleapis.com
   ```

4. **Service Account**
   ```bash
   # Create service account for Terraform
   gcloud iam service-accounts create terraform-sa \
     --display-name "Terraform Service Account"
   
   # Grant necessary permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/editor"
   
   # Create and download key
   gcloud iam service-accounts keys create terraform-key.json \
     --iam-account=terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com
   
   # Set credentials
   export GOOGLE_APPLICATION_CREDENTIALS=terraform-key.json
   ```

## Deployment Steps

### 1. Create Terraform State Bucket

```bash
# Create GCS bucket for Terraform state
gsutil mb -p $PROJECT_ID -l asia-south1 gs://trading-platform-terraform-state

# Enable versioning
gsutil versioning set on gs://trading-platform-terraform-state
```

### 2. Configure Variables

Create `terraform.tfvars`:

```hcl
project_id              = "your-project-id"
region                  = "asia-south1"
environment             = "prod"
db_instance_tier        = "db-custom-4-16384"
redis_memory_size_gb    = 5
redis_tier              = "STANDARD_HA"
enable_read_replicas    = true
backup_retention_days   = 7
```

### 3. Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 4. Plan Infrastructure

```bash
# Review planned changes
terraform plan -out=tfplan
```

### 5. Apply Infrastructure

```bash
# Apply changes
terraform apply tfplan

# Save outputs
terraform output -json > outputs.json
```

### 6. Initialize Database

```bash
# Get database connection details
export DB_HOST=$(terraform output -raw cloudsql_private_ip)
export DB_NAME=$(terraform output -raw database_name)
export DB_USER=$(terraform output -raw database_user)
export DB_PASSWORD=$(terraform output -raw database_password)

# Run initialization script
cd ../scripts
chmod +x init-database.sh
./init-database.sh
```

## PgBouncer Setup

PgBouncer provides connection pooling to reduce database connection overhead.

### Configuration

```bash
# Set up PgBouncer
cd infrastructure/scripts
chmod +x setup-pgbouncer.sh
./setup-pgbouncer.sh
```

### Connection Pooling Benefits

- **Reduced Overhead**: Reuse connections instead of creating new ones
- **Better Performance**: Lower latency for database operations
- **Resource Efficiency**: Fewer connections to database server
- **Scalability**: Support more concurrent clients

### Connection Strings

```bash
# Direct connection (for migrations)
postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}

# Through PgBouncer (for application)
postgresql://${DB_USER}:${DB_PASSWORD}@pgbouncer:6432/${DB_NAME}
```

## Monitoring

### Cloud SQL Monitoring

```bash
# View instance status
gcloud sql instances describe trading-platform-db-prod

# View operations
gcloud sql operations list --instance=trading-platform-db-prod

# View backups
gcloud sql backups list --instance=trading-platform-db-prod
```

### Redis Monitoring

```bash
# View instance status
gcloud redis instances describe trading-platform-redis-prod --region=asia-south1

# View operations
gcloud redis operations list --region=asia-south1
```

### Query Insights

Cloud SQL Query Insights provides detailed query performance metrics:
- Slow query identification
- Query execution statistics
- Resource consumption analysis

Access via: Cloud Console → SQL → Instance → Query Insights

## Maintenance

### Backup and Restore

```bash
# Create on-demand backup
gcloud sql backups create --instance=trading-platform-db-prod

# List backups
gcloud sql backups list --instance=trading-platform-db-prod

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=trading-platform-db-prod \
  --backup-id=BACKUP_ID
```

### Scaling

```bash
# Update instance tier
terraform apply -var="db_instance_tier=db-custom-8-32768"

# Update Redis memory
terraform apply -var="redis_memory_size_gb=10"
```

### Maintenance Windows

- **Cloud SQL**: Sunday 3:00 AM IST
- **Redis**: Sunday 3:00 AM IST

Updates are applied automatically during maintenance windows.

## Cost Optimization

### Estimated Monthly Costs (Mumbai Region)

- **Cloud SQL Primary**: ~$400/month (4 vCPU, 16GB RAM, HA)
- **Cloud SQL Replica**: ~$300/month (4 vCPU, 16GB RAM)
- **Redis Standard HA**: ~$250/month (5GB)
- **Network Egress**: ~$50/month
- **Total**: ~$1000/month

### Cost Reduction Tips

1. **Development Environment**: Use smaller instances
   ```hcl
   db_instance_tier = "db-custom-2-8192"  # 2 vCPU, 8GB RAM
   redis_memory_size_gb = 2
   redis_tier = "BASIC"  # No HA for dev
   enable_read_replicas = false
   ```

2. **Scheduled Scaling**: Scale down during off-market hours

3. **Committed Use Discounts**: 1-year or 3-year commitments for 25-50% savings

## Security

### Network Security
- All resources in private VPC
- No public IP addresses
- SSL/TLS required for all connections
- VPC Service Controls for additional isolation

### Access Control
- IAM-based access control
- Service accounts with minimal permissions
- Audit logging enabled
- Secret Manager for credentials

### Compliance
- Automated backups with encryption at rest
- Point-in-time recovery enabled
- Transaction logs retained for 7 days
- Deletion protection enabled on production

## Troubleshooting

### Connection Issues

```bash
# Test Cloud SQL connection
gcloud sql connect trading-platform-db-prod --user=trading_user

# Test Redis connection
gcloud redis instances describe trading-platform-redis-prod --region=asia-south1
```

### Performance Issues

```bash
# Check Cloud SQL metrics
gcloud monitoring time-series list \
  --filter='resource.type="cloudsql_database"'

# Check Redis metrics
gcloud monitoring time-series list \
  --filter='resource.type="redis_instance"'
```

### Backup Issues

```bash
# Verify backup configuration
gcloud sql instances describe trading-platform-db-prod \
  --format="value(settings.backupConfiguration)"
```

## Cleanup

```bash
# Destroy all infrastructure (WARNING: Deletes all data)
terraform destroy

# Delete state bucket
gsutil rm -r gs://trading-platform-terraform-state
```

## Next Steps

- Configure Cloud Run services (Task 14.3)
- Set up Secret Manager (Task 14.4)
- Configure Load Balancer (Task 14.5)
- Set up monitoring and logging (Task 14.6)
