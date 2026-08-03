#!/usr/bin/env bash
set -euo pipefail

# Scope this entire script to a dedicated "clearslate" gcloud configuration instead of
# whatever configuration the caller currently has active. Without this, `gcloud config
# configurations create clearslate` would activate it as a side effect, and a bare
# `gcloud config set project` on a re-run would silently repoint the caller's ACTIVE
# config (which might be a totally unrelated project) rather than this one.
export CLOUDSDK_ACTIVE_CONFIG_NAME=clearslate

# ClearSlate GCP Bootstrap Script — Tasks 0.1 + 0.4 (+ Task 1.15 build prerequisites)
# Configures a GCP project for local development and deployment.
# Usage: PROJECT_ID=your-project-id BILLING_ACCOUNT_ID=your-billing-id scripts/bootstrap_gcp.sh
#
# Every gcloud call below passes --project (or a positional PROJECT_ID) explicitly —
# this script never relies on, and never sets, an ambient default project.

PROJECT_ID=${PROJECT_ID:?set PROJECT_ID}
BILLING_ACCOUNT_ID=${BILLING_ACCOUNT_ID:?set BILLING_ACCOUNT_ID}
REGION=us-central1
SERVICE_ACCOUNT=clearslate-run
STAGING_BUCKET=gs://clearslate-hackathon-agent-staging
RUNS_BUCKET=gs://clearslate-hackathon-runs
PARALLEL_SECRET=parallel-api-key

echo "Bootstrapping ClearSlate GCP project: $PROJECT_ID"

# Authenticate with Application Default Credentials
echo "Ensure you are authenticated: gcloud auth application-default login"

# Runs a "create"-style gcloud command, tolerating only an "already exists" failure so
# re-running this script is safe. Any other failure (auth, quota, typos, ...) is
# surfaced and aborts the script rather than being silently swallowed.
run_idempotent() {
  local err
  if ! err=$("$@" 2>&1); then
    if echo "$err" | grep -qi "already exists"; then
      echo "  (already exists, continuing)"
    else
      echo "$err" >&2
      exit 1
    fi
  fi
}

# Create (but do not activate) the dedicated gcloud configuration. CLOUDSDK_ACTIVE_CONFIG_NAME
# above already scopes every gcloud call in this script to it; --no-activate means this
# script never changes which configuration is active for the caller's shell.
echo "Creating gcloud configuration 'clearslate' (if needed)..."
run_idempotent gcloud config configurations create clearslate --no-activate

# Create the GCP project (errors harmlessly if it already exists)
echo "Creating GCP project (if needed)..."
run_idempotent gcloud projects create "$PROJECT_ID"

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
run_idempotent gcloud firestore databases create \
  --location="$REGION" \
  --type=firestore-native \
  --project="$PROJECT_ID"

# Create storage buckets
echo "Creating GCS buckets..."
run_idempotent gcloud storage buckets create "$STAGING_BUCKET" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --project="$PROJECT_ID"
run_idempotent gcloud storage buckets create "$RUNS_BUCKET" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --project="$PROJECT_ID"

# Create service account
echo "Creating service account..."
run_idempotent gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
  --display-name="ClearSlate run worker" \
  --project="$PROJECT_ID"

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
  --role="roles/storage.objectAdmin" \
  --project="$PROJECT_ID"

# Task 0.4 — Parallel API key secret
echo "Creating Secret Manager secret '$PARALLEL_SECRET' (if needed)..."
run_idempotent gcloud secrets create "$PARALLEL_SECRET" \
  --replication-policy=automatic \
  --project="$PROJECT_ID"

# This script does NOT populate the secret (never put a real API key inline in a
# script or your shell history). After bootstrapping, add your key with:
#   printf '%s' "$YOUR_PARALLEL_API_KEY" | \
#     gcloud secrets versions add "$PARALLEL_SECRET" --data-file=- --project="$PROJECT_ID"

echo "Granting secretAccessor on '$PARALLEL_SECRET' to $SA_EMAIL..."
gcloud secrets add-iam-policy-binding "$PARALLEL_SECRET" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor" \
  --project="$PROJECT_ID"

# Task 1.15 prerequisite — `gcloud run deploy --source` builds the container via Cloud
# Build, which runs as the default Compute Engine service account. Projects created
# after Google's 2024-05-01 change to default service account permissions no longer
# auto-grant that account the roles Cloud Build needs, so `gcloud run deploy --source .`
# fails at build time without these explicit grants.
echo "Granting Cloud Build roles to the default Compute service account..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
COMPUTE_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

for role in \
  roles/storage.objectViewer \
  roles/artifactregistry.writer \
  roles/logging.logWriter \
  roles/cloudbuild.builds.builder; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="$role" \
    --condition=None
done

echo "✓ ClearSlate GCP bootstrap complete."
echo ""
echo "Next: Authenticate locally with ADC and set .env vars:"
echo "  gcloud auth application-default login"
echo "  cp .env.example .env"
echo "  # Edit .env: set GOOGLE_CLOUD_PROJECT and PARALLEL_API_KEY"
echo "  # Populate the Secret Manager key too (see comment above the secretAccessor grant)"
