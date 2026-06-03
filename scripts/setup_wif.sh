#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
GITHUB_REPO="${GITHUB_REPO:-<owner>/<repo>}" # Overridden by git remote auto-detection below.

# Detect git remote
REMOTE_URL=$(git config --get remote.origin.url)
# Convert git@github.com:User/Repo.git to User/Repo
if [[ "$REMOTE_URL" =~ github\.com[:/](.+)/(.+)(\.git)?$ ]]; then
    GITHUB_OWNER=${BASH_REMATCH[1]}
    GITHUB_REPO_NAME=${BASH_REMATCH[2]}
    GITHUB_REPO="${GITHUB_OWNER}/${GITHUB_REPO_NAME%.git}"
else
    echo "Could not detect GitHub repo from git config. Please set GITHUB_REPO manually in the script."
    echo "Detected URL: $REMOTE_URL"
    exit 1
fi

SERVICE_ACCOUNT="github-actions-deployer"
POOL_NAME="github-actions-pool-1"
PROVIDER_NAME="github-actions-provider-1"
REGION="global" # WIF pools are global

echo "Setting up Workload Identity Federation for:"
echo "  Project: $PROJECT_ID"
echo "  Repo:    $GITHUB_REPO"
echo "------------------------------------------------"

# 1. Create Service Account
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    echo "Service Account ${SERVICE_ACCOUNT} already exists."
else
    echo "Creating Service Account..."
    gcloud iam service-accounts create "${SERVICE_ACCOUNT}" \
      --display-name="GitHub Actions Deployer"
fi

# 2. Grant Permissions
echo "Granting roles..."
# Cloud Run Developer
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.developer" &>/dev/null

# Service Account User (to act as itself)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" &>/dev/null

# Storage Admin (for pushing to GCR/Artifact Registry)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin" &>/dev/null
  
# Artifact Registry Writer (if using Artifact Registry in future)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer" &>/dev/null

# 3. Create Workload Identity Pool
if gcloud iam workload-identity-pools describe "${POOL_NAME}" --location="${REGION}" &>/dev/null; then
    echo "Pool ${POOL_NAME} already exists."
else
    echo "Creating Workload Identity Pool..."
    gcloud iam workload-identity-pools create "${POOL_NAME}" \
      --location="${REGION}" \
      --display-name="GitHub Actions Pool"
fi

# Get Pool ID
POOL_ID=$(gcloud iam workload-identity-pools describe "${POOL_NAME}" --location="${REGION}" --format='value(name)')

# 4. Create Provider
if gcloud iam workload-identity-pools providers describe "${PROVIDER_NAME}" --location="${REGION}" --workload-identity-pool="${POOL_NAME}" &>/dev/null; then
    echo "Provider ${PROVIDER_NAME} already exists."
else
    echo "Creating Provider..."
    echo "Creating Provider..."
    gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_NAME}" \
      --location="${REGION}" \
      --workload-identity-pool="${POOL_NAME}" \
      --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
      --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
      --issuer-uri="https://token.actions.githubusercontent.com"
fi

# 5. Allow GitHub Repo to impersonate Service Account
echo "Binding Service Account to Pool..."
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${GITHUB_REPO}" &>/dev/null

# 6. Output Secrets
PROVIDER_ID=$(gcloud iam workload-identity-pools providers describe "${PROVIDER_NAME}" --location="${REGION}" --workload-identity-pool="${POOL_NAME}" --format='value(name)')

echo ""
echo "===================================================="
echo "SETUP COMPLETE!"
echo "Please set the following secrets in GitHub (Settings > Secrets and variables > Actions):"
echo ""
echo "GCP_PROJECT_ID:           ${PROJECT_ID}"
echo "GCP_WIF_PROVIDER:         ${PROVIDER_ID}"
echo "GCP_SERVICE_ACCOUNT:      ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
echo "===================================================="
