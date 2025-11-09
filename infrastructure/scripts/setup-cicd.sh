#!/bin/bash
# Setup CI/CD Pipeline with Cloud Build

set -e

PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REPO_NAME=${REPO_NAME:-"trading-platform"}
REPO_OWNER=${REPO_OWNER:-"your-github-username"}
BRANCH=${BRANCH:-"main"}

echo "Setting up CI/CD pipeline for project: $PROJECT_ID"
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Branch: $BRANCH"
echo ""

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
  --project=$PROJECT_ID

gcloud services enable run.googleapis.com \
  --project=$PROJECT_ID

gcloud services enable containerregistry.googleapis.com \
  --project=$PROJECT_ID

echo "✓ APIs enabled"
echo ""

# Grant Cloud Build permissions
echo "Granting Cloud Build permissions..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/storage.admin"

echo "✓ Permissions granted"
echo ""

# Create build trigger for staging (automatic on push)
echo "Creating staging build trigger..."
gcloud builds triggers create github \
  --name="trading-platform-staging" \
  --repo-name=$REPO_NAME \
  --repo-owner=$REPO_OWNER \
  --branch-pattern="^${BRANCH}$" \
  --build-config=cloudbuild.yaml \
  --description="Automatic build and deploy to staging on push to $BRANCH" \
  --project=$PROJECT_ID

echo "✓ Staging trigger created"
echo ""

# Create build trigger for production (manual approval required)
echo "Creating production build trigger..."
gcloud builds triggers create github \
  --name="trading-platform-production" \
  --repo-name=$REPO_NAME \
  --repo-owner=$REPO_OWNER \
  --tag-pattern="^v[0-9]+\.[0-9]+\.[0-9]+$" \
  --build-config=cloudbuild-prod.yaml \
  --description="Manual production deployment on version tag" \
  --project=$PROJECT_ID \
  --require-approval

echo "✓ Production trigger created"
echo ""

# Create notification config for build status
echo "Creating build notification..."
gcloud builds triggers create github \
  --name="trading-platform-notifications" \
  --repo-name=$REPO_NAME \
  --repo-owner=$REPO_OWNER \
  --branch-pattern=".*" \
  --build-config=cloudbuild.yaml \
  --description="Build status notifications" \
  --project=$PROJECT_ID \
  --subscription-filter="build.status=SUCCESS OR build.status=FAILURE"

echo "✓ Notifications configured"
echo ""

echo "CI/CD pipeline setup complete!"
echo ""
echo "Next steps:"
echo "1. Connect your GitHub repository in Cloud Console"
echo "2. Push to $BRANCH branch to trigger staging deployment"
echo "3. Create a version tag (e.g., v1.0.0) to trigger production deployment"
echo "4. Approve production deployment in Cloud Console"
