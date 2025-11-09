#!/bin/bash
# Secret Manager Management Script

set -e

PROJECT_ID=${PROJECT_ID:-"your-project-id"}
COMMAND=${1:-"list"}

case $COMMAND in
  list)
    echo "Listing all secrets..."
    gcloud secrets list --project=$PROJECT_ID
    ;;
    
  create)
    SECRET_NAME=$2
    SECRET_VALUE=$3
    
    if [ -z "$SECRET_NAME" ] || [ -z "$SECRET_VALUE" ]; then
      echo "Usage: $0 create SECRET_NAME SECRET_VALUE"
      exit 1
    fi
    
    echo "Creating secret: $SECRET_NAME"
    echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME \
      --data-file=- \
      --replication-policy="automatic" \
      --project=$PROJECT_ID
    
    echo "✓ Secret created successfully"
    ;;
    
  update)
    SECRET_NAME=$2
    SECRET_VALUE=$3
    
    if [ -z "$SECRET_NAME" ] || [ -z "$SECRET_VALUE" ]; then
      echo "Usage: $0 update SECRET_NAME SECRET_VALUE"
      exit 1
    fi
    
    echo "Updating secret: $SECRET_NAME"
    echo -n "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME \
      --data-file=- \
      --project=$PROJECT_ID
    
    echo "✓ Secret updated successfully"
    ;;
    
  get)
    SECRET_NAME=$2
    
    if [ -z "$SECRET_NAME" ]; then
      echo "Usage: $0 get SECRET_NAME"
      exit 1
    fi
    
    echo "Getting secret: $SECRET_NAME"
    gcloud secrets versions access latest \
      --secret=$SECRET_NAME \
      --project=$PROJECT_ID
    ;;
    
  delete)
    SECRET_NAME=$2
    
    if [ -z "$SECRET_NAME" ]; then
      echo "Usage: $0 delete SECRET_NAME"
      exit 1
    fi
    
    echo "Deleting secret: $SECRET_NAME"
    gcloud secrets delete $SECRET_NAME \
      --project=$PROJECT_ID \
      --quiet
    
    echo "✓ Secret deleted successfully"
    ;;
    
  grant-access)
    SECRET_NAME=$2
    SERVICE_ACCOUNT=$3
    
    if [ -z "$SECRET_NAME" ] || [ -z "$SERVICE_ACCOUNT" ]; then
      echo "Usage: $0 grant-access SECRET_NAME SERVICE_ACCOUNT"
      exit 1
    fi
    
    echo "Granting access to secret: $SECRET_NAME"
    gcloud secrets add-iam-policy-binding $SECRET_NAME \
      --member="serviceAccount:${SERVICE_ACCOUNT}" \
      --role="roles/secretmanager.secretAccessor" \
      --project=$PROJECT_ID
    
    echo "✓ Access granted successfully"
    ;;
    
  rotate)
    SECRET_NAME=$2
    NEW_VALUE=$3
    
    if [ -z "$SECRET_NAME" ] || [ -z "$NEW_VALUE" ]; then
      echo "Usage: $0 rotate SECRET_NAME NEW_VALUE"
      exit 1
    fi
    
    echo "Rotating secret: $SECRET_NAME"
    
    # Add new version
    echo -n "$NEW_VALUE" | gcloud secrets versions add $SECRET_NAME \
      --data-file=- \
      --project=$PROJECT_ID
    
    # Disable old versions (keep last 2)
    VERSIONS=$(gcloud secrets versions list $SECRET_NAME \
      --project=$PROJECT_ID \
      --format="value(name)" \
      --sort-by="~name" \
      --limit=100)
    
    COUNT=0
    for VERSION in $VERSIONS; do
      COUNT=$((COUNT + 1))
      if [ $COUNT -gt 2 ]; then
        echo "Disabling version: $VERSION"
        gcloud secrets versions disable $VERSION \
          --secret=$SECRET_NAME \
          --project=$PROJECT_ID \
          --quiet
      fi
    done
    
    echo "✓ Secret rotated successfully"
    ;;
    
  setup-broker)
    echo "Setting up broker API keys..."
    echo ""
    echo "Please enter your broker API credentials:"
    echo ""
    
    read -p "Angel One API Key: " ANGEL_API_KEY
    read -sp "Angel One API Secret: " ANGEL_API_SECRET
    echo ""
    read -p "Angel One Client Code: " ANGEL_CLIENT_CODE
    read -sp "Angel One Password: " ANGEL_PASSWORD
    echo ""
    read -sp "Angel One TOTP Secret: " ANGEL_TOTP_SECRET
    echo ""
    
    # Create JSON with credentials
    BROKER_CREDS=$(cat <<EOF
{
  "api_key": "$ANGEL_API_KEY",
  "api_secret": "$ANGEL_API_SECRET",
  "client_code": "$ANGEL_CLIENT_CODE",
  "password": "$ANGEL_PASSWORD",
  "totp_secret": "$ANGEL_TOTP_SECRET"
}
EOF
)
    
    echo "Creating/updating angel-one-api-key secret..."
    echo -n "$BROKER_CREDS" | gcloud secrets versions add angel-one-api-key \
      --data-file=- \
      --project=$PROJECT_ID
    
    echo "✓ Broker credentials configured successfully"
    ;;
    
  *)
    echo "Usage: $0 {list|create|update|get|delete|grant-access|rotate|setup-broker}"
    echo ""
    echo "Commands:"
    echo "  list                                    - List all secrets"
    echo "  create SECRET_NAME SECRET_VALUE         - Create a new secret"
    echo "  update SECRET_NAME SECRET_VALUE         - Update existing secret"
    echo "  get SECRET_NAME                         - Get secret value"
    echo "  delete SECRET_NAME                      - Delete a secret"
    echo "  grant-access SECRET_NAME SERVICE_ACCOUNT - Grant access to service account"
    echo "  rotate SECRET_NAME NEW_VALUE            - Rotate secret and disable old versions"
    echo "  setup-broker                            - Interactive broker credentials setup"
    exit 1
    ;;
esac
