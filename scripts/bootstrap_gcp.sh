#!/usr/bin/env bash
set -euo pipefail

# ClearSlate GCP Bootstrap Script — Task 0.1
# Configures a GCP project for local development and deployment.
# Usage: PROJECT_ID=your-project-id BILLING_ACCOUNT_ID=your-billing-id scripts/bootstrap_gcp.sh

PROJECT_ID=${PROJECT_ID:?set PROJECT_ID}
BILLING_ACCOUNT_ID=${BILLING_ACCOUNT_ID:?set BILLING_ACCOUNT_ID}
REGION=us-central1
SERVICE_ACCOUNT=clearslate-run
STAGING_BUCKET=gs://clearslate-hackathon-agent-staging
RUNS_BUCKET=gs://clearslate-hackathon-runs

echo "Bootstrapping ClearSlate GCP project: $PROJECT_ID"

# Authenticate with Application Default Credentials
echo "Ensure you are authenticated: gcloud auth application-default login"

# Set the project configuration
gcloud config configurations create clearslate 2>/dev/null || true
gcloud config set project "$PROJECT_ID"

# Create the GCP project (errors harmlessly if it already exists)
echo "Creating GCP project (if needed)..."
gcloud projects create "$PROJECT_ID" 2>/dev/null || echo "Project $PROJECT_ID already exists."

# Link billing account
echo "Linking billing account..."
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"

# Enable required APIs
echo "Enabling APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  discoveryengine.googleapis.com \
  --project="$PROJECT_ID"

# Create Firestore database (native mode, us-central1)
echo "Creating Firestore database (if needed)..."
gcloud firestore databases create \
  --location="$REGION" \
  --type=firestore-native \
  --project="$PROJECT_ID" 2>/dev/null || echo "Firestore database already exists."

# Create storage buckets
echo "Creating GCS buckets..."
gsutil mb -p "$PROJECT_ID" "$STAGING_BUCKET" 2>/dev/null || echo "Bucket $STAGING_BUCKET already exists."
gsutil mb -p "$PROJECT_ID" "$RUNS_BUCKET" 2>/dev/null || echo "Bucket $RUNS_BUCKET already exists."

# Create service account
echo "Creating service account..."
gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
  --display-name="ClearSlate run worker" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Service account $SERVICE_ACCOUNT already exists."

SA_EMAIL="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"

# Grant roles to service account
echo "Granting IAM roles to $SA_EMAIL..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/aiplatform.user" \
  --condition=None

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/datastore.user" \
  --condition=None

# Grant storage.objectAdmin on the runs bucket only
gcloud storage buckets add-iam-policy-binding "$RUNS_BUCKET" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"

echo "✓ ClearSlate GCP bootstrap complete."
echo ""
echo "Next: Authenticate locally with ADC and set .env vars:"
echo "  gcloud auth application-default login"
echo "  cp .env.example .env"
echo "  # Edit .env: set GOOGLE_CLOUD_PROJECT and PARALLEL_API_KEY"
