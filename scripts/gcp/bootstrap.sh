#!/usr/bin/env bash
# One-time GCP setup. Usage (from repo root): bash scripts/gcp/bootstrap.sh

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
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$GCP_PROJECT_ID"

grant_secret_access

log "Ensuring Secret Manager entries exist (add values in Console)..."
for secret_id in "${REQUIRED_SECRETS[@]}"; do
  if secret_exists "$secret_id"; then
    log "  exists: $secret_id"
  else
    gcloud secrets create "$secret_id" \
      --project="$GCP_PROJECT_ID" \
      --replication-policy=automatic \
      --quiet
    log "  created: $secret_id (add a version in Console)"
  fi
done

log "Bootstrap complete."
echo ""
echo "Next: add secret values in Secret Manager (if not done):"
echo "  https://console.cloud.google.com/security/secret-manager?project=${GCP_PROJECT_ID}"
echo ""
echo "Then deploy:"
echo "  bash scripts/gcp/deploy.sh"
