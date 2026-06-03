#!/bin/bash
# scripts/setup_iam.sh

# Configuration
PROJECT_ID="${PROJECT_ID:?PROJECT_ID is required (e.g. export PROJECT_ID=my-gcp-project)}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-stock-web-ui-sa}"
BUCKET_NAME="${BUCKET_NAME:?BUCKET_NAME is required (e.g. export BUCKET_NAME=my-bucket)}"
CRON_SA_NAME="${CRON_SA_NAME:-stock-cron-sa}"

echo "Setting up IAM for Project: $PROJECT_ID"

# 1. Cloud Run Service Account -> Secret Manager Access
# Assuming the secret is named "SLACK_WEBHOOK", "XXXX_API_KEY", "XXXX_API_SECRET" etc.
# We grant 'roles/secretmanager.secretAccessor' to the Service Account.

echo "Granting Secret Manager Accessor to $SERVICE_ACCOUNT_NAME..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# 2. Cloud Run -> GCS Access
echo "Granting GCS Object Admin to $SERVICE_ACCOUNT_NAME for bucket $BUCKET_NAME..."
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://$BUCKET_NAME

# 3. Enable Cloud Logging (if not already enabled)
echo "Enabling Cloud Logging API..."
gcloud services enable logging.googleapis.com

# 4. Cron Service Account Permissions (if separate)
# If existing GCE instance is used, check its service account.
# Assuming we create a dedicated one for cron jobs if using Cloud Scheduler + Cloud Run Jobs in future.
# For now, if using GCE, ensure GCE SA has write access to GCS.

echo "IAM setup complete."
