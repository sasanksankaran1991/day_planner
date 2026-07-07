#!/usr/bin/env bash
# One-time GCP setup (like individual_ikr).
# Usage (from repo root): bash scripts/gcp/bootstrap.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

log "Project: $GCP_PROJECT_ID  Region: $GCP_REGION"

gcloud config set project "$GCP_PROJECT_ID"

log "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com \
  --project="$GCP_PROJECT_ID"

if ! gcloud artifacts repositories describe "$AR_REPO" \
  --location="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
  log "Creating Artifact Registry repo: $AR_REPO"
  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$GCP_REGION" \
    --description="Day Planner Docker images"
else
  log "Artifact Registry repo exists: $AR_REPO"
fi

if ! gcloud storage buckets describe "gs://${GCS_DATA_BUCKET}" &>/dev/null; then
  log "Creating GCS bucket: $GCS_DATA_BUCKET"
  gcloud storage buckets create "gs://${GCS_DATA_BUCKET}" \
    --project="$GCP_PROJECT_ID" \
    --location="$GCP_REGION" \
    --uniform-bucket-level-access
else
  log "GCS bucket exists: $GCS_DATA_BUCKET"
fi

RUNNER_EMAIL="$(runner_sa_email)"
SCHEDULER_EMAIL="$(scheduler_sa_email)"

for sa in "$RUNNER_SA" "$SCHEDULER_SA"; do
  email="${sa}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
  if ! gcloud iam service-accounts describe "$email" --project="$GCP_PROJECT_ID" &>/dev/null; then
    log "Creating service account: $sa"
    gcloud iam service-accounts create "$sa" \
      --project="$GCP_PROJECT_ID" \
      --display-name="$sa"
  fi
done

log "Granting IAM to runner SA..."
for role in secretmanager.secretAccessor storage.objectAdmin; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:${RUNNER_EMAIL}" \
    --role="roles/${role}" \
    --quiet >/dev/null
done

gcloud storage buckets add-iam-policy-binding "gs://${GCS_DATA_BUCKET}" \
  --member="serviceAccount:${RUNNER_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --quiet >/dev/null

PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" \
  --location="$GCP_REGION" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/artifactregistry.writer" \
  --quiet >/dev/null

gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${SCHEDULER_EMAIL}" \
  --role="roles/run.invoker" \
  --quiet >/dev/null

log "Ensuring Secret Manager entries exist..."
for secret_id in "${REQUIRED_SECRETS[@]}"; do
  if secret_exists "$secret_id"; then
    log "  exists: $secret_id"
  else
    gcloud secrets create "$secret_id" \
      --project="$GCP_PROJECT_ID" \
      --replication-policy=automatic \
      --quiet
    log "  created: $secret_id (add value in Console)"
  fi
done

log "Bootstrap complete."
echo ""
echo "Next:"
echo "  1. Add secret values in Secret Manager (if not done)"
echo "  2. bash scripts/gcp/deploy.sh"
