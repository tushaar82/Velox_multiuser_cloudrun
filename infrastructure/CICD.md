# CI/CD Pipeline Guide

This guide explains the CI/CD pipeline setup for the trading platform using Google Cloud Build.

## Overview

The platform uses a two-stage deployment pipeline:
1. **Staging**: Automatic deployment on push to main branch
2. **Production**: Manual approval required, triggered by version tags

## Pipeline Architecture

```
GitHub Push (main branch)
    ↓
[Cloud Build Trigger]
    ↓
┌─────────────────────┐
│ 1. Run Tests        │
│ 2. Build Images     │
│ 3. Push to GCR      │
│ 4. Deploy Staging   │
│ 5. Smoke Tests      │
└─────────────────────┘
    ↓
[Staging Environment]

GitHub Tag (v1.0.0)
    ↓
[Cloud Build Trigger]
    ↓
[Manual Approval Required]
    ↓
┌─────────────────────┐
│ 1. Deploy (no traffic) │
│ 2. Smoke Tests      │
│ 3. 10% Traffic      │
│ 4. Check Metrics    │
│ 5. 50% Traffic      │
│ 6. 100% Traffic     │
└─────────────────────┘
    ↓
[Production Environment]
```

## Setup

### 1. Prerequisites

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Authenticate
gcloud auth login

# Set project
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID
```

### 2. Connect GitHub Repository

```bash
# Go to Cloud Console
# Cloud Build → Triggers → Connect Repository
# Select GitHub and authorize
# Choose your repository
```

### 3. Run Setup Script

```bash
cd infrastructure/scripts
chmod +x setup-cicd.sh

# Configure variables
export PROJECT_ID=your-project-id
export REPO_NAME=trading-platform
export REPO_OWNER=your-github-username
export BRANCH=main

# Run setup
./setup-cicd.sh
```

## Build Triggers

### Staging Trigger

- **Name**: `trading-platform-staging`
- **Event**: Push to `main` branch
- **Config**: `cloudbuild.yaml`
- **Approval**: Not required (automatic)

**Steps**:
1. Run unit tests
2. Build Docker images
3. Push images to GCR
4. Deploy to staging
5. Run smoke tests

### Production Trigger

- **Name**: `trading-platform-production`
- **Event**: Tag matching `v*.*.*` (e.g., v1.0.0)
- **Config**: `cloudbuild-prod.yaml`
- **Approval**: Required (manual)

**Steps**:
1. Deploy new revision (no traffic)
2. Run smoke tests
3. Migrate 10% traffic
4. Check metrics
5. Migrate 50% traffic
6. Migrate 100% traffic (complete)

## Deployment Process

### Staging Deployment

```bash
# Make changes
git add .
git commit -m "Add new feature"
git push origin main

# Automatic deployment triggered
# View build status
gcloud builds list --limit=5

# View logs
gcloud builds log BUILD_ID --stream
```

### Production Deployment

```bash
# Create version tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Build triggered (requires approval)
# Go to Cloud Console → Cloud Build → History
# Click on build → Approve

# Monitor deployment
gcloud builds log BUILD_ID --stream
```

## Rolling Update Strategy

Production deployments use gradual traffic migration:

1. **Deploy (0% traffic)**: New revision deployed without traffic
2. **Smoke Tests**: Verify new revision works
3. **10% Traffic**: Migrate 10% of traffic, monitor for 5 minutes
4. **Check Metrics**: Verify error rate < 5%
5. **50% Traffic**: Migrate 50% of traffic, monitor for 5 minutes
6. **100% Traffic**: Complete migration

### Rollback

If issues detected during migration:

```bash
# Get previous revision
PREV_REV=$(gcloud run revisions list \
  --service=api-gateway \
  --region=asia-south1 \
  --format='value(metadata.name)' \
  --limit=2 | tail -1)

# Rollback to previous revision
gcloud run services update-traffic api-gateway \
  --region=asia-south1 \
  --to-revisions=$PREV_REV=100
```

## Build Configuration

### cloudbuild.yaml (Staging)

```yaml
steps:
  - name: 'python:3.11-slim'
    id: 'run-tests'
    # Run pytest
  
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-images'
    # Build Docker images
  
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-images'
    # Push to GCR
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-staging'
    # Deploy to Cloud Run
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'smoke-tests'
    # Run smoke tests
```

### cloudbuild-prod.yaml (Production)

```yaml
steps:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-production'
    # Deploy with no traffic
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'smoke-tests'
    # Run smoke tests
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'traffic-10'
    # Migrate 10% traffic
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'check-metrics'
    # Verify metrics
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'traffic-50'
    # Migrate 50% traffic
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'traffic-100'
    # Complete migration
```

## Monitoring Builds

### View Build History

```bash
# List recent builds
gcloud builds list --limit=10

# View specific build
gcloud builds describe BUILD_ID

# Stream build logs
gcloud builds log BUILD_ID --stream
```

### Build Status

```bash
# Check build status
gcloud builds describe BUILD_ID --format='value(status)'

# Possible statuses:
# - QUEUED: Build is queued
# - WORKING: Build is in progress
# - SUCCESS: Build completed successfully
# - FAILURE: Build failed
# - CANCELLED: Build was cancelled
# - TIMEOUT: Build timed out
```

### Build Notifications

Configure Slack/Email notifications:

```bash
# Create Pub/Sub topic
gcloud pubsub topics create cloud-builds

# Create subscription
gcloud pubsub subscriptions create cloud-builds-sub \
  --topic=cloud-builds

# Configure notification
gcloud builds triggers update trading-platform-staging \
  --subscription-filter="build.status=SUCCESS OR build.status=FAILURE"
```

## Testing

### Unit Tests

Run automatically in CI pipeline:

```bash
pytest tests/ --cov=. --cov-report=term --cov-report=xml -v
```

### Smoke Tests

Verify basic functionality:

```bash
# Health check
curl -f https://staging.example.com/health

# API test
curl -f https://staging.example.com/api/health
```

### Integration Tests

Run manually before production:

```bash
# Run integration tests
pytest tests/integration/ -v
```

## Security

### Build Service Account

Cloud Build uses a service account with minimal permissions:

```bash
# View permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
```

### Secret Management

Secrets are stored in Secret Manager:

```bash
# Access secret in build
gcloud secrets versions access latest --secret=SECRET_NAME
```

### Image Scanning

Enable vulnerability scanning:

```bash
# Enable Container Analysis API
gcloud services enable containeranalysis.googleapis.com

# View vulnerabilities
gcloud container images describe gcr.io/$PROJECT_ID/api-gateway:latest \
  --show-package-vulnerability
```

## Cost Optimization

### Estimated Costs

- **Cloud Build**: $0.003/build-minute (first 120 minutes/day free)
- **Container Registry**: $0.026/GB/month storage
- **Estimated Total**: $20-50/month (depending on build frequency)

### Cost Reduction Tips

1. **Optimize Build Time**: Use caching, parallel builds
2. **Clean Old Images**: Delete unused images regularly
3. **Use Smaller Machines**: E2_HIGHCPU_8 for faster builds

```bash
# Delete old images
gcloud container images list-tags gcr.io/$PROJECT_ID/api-gateway \
  --filter='-tags:*' \
  --format='get(digest)' \
  --limit=10 | \
  xargs -I {} gcloud container images delete gcr.io/$PROJECT_ID/api-gateway@{} --quiet
```

## Troubleshooting

### Build Fails

```bash
# View build logs
gcloud builds log BUILD_ID

# Common issues:
# 1. Test failures - Fix tests
# 2. Docker build errors - Check Dockerfile
# 3. Permission errors - Check IAM roles
# 4. Timeout - Increase timeout in cloudbuild.yaml
```

### Deployment Fails

```bash
# Check Cloud Run logs
gcloud run services logs read api-gateway \
  --region=asia-south1 \
  --limit=50

# Check revision status
gcloud run revisions describe REVISION_NAME \
  --region=asia-south1
```

### Rollback Failed Deployment

```bash
# List revisions
gcloud run revisions list \
  --service=api-gateway \
  --region=asia-south1

# Rollback to previous
gcloud run services update-traffic api-gateway \
  --region=asia-south1 \
  --to-revisions=PREVIOUS_REVISION=100
```

## Best Practices

1. **Version Tags**: Use semantic versioning (v1.0.0)
2. **Commit Messages**: Clear, descriptive messages
3. **Test Coverage**: Maintain > 80% coverage
4. **Code Review**: Require PR reviews before merge
5. **Staging First**: Always test in staging
6. **Monitor Metrics**: Watch error rates during deployment
7. **Rollback Plan**: Have rollback procedure ready

## Next Steps

- Perform load testing (Task 14.8)
- Set up automated integration tests
- Configure deployment notifications
- Implement canary deployments
