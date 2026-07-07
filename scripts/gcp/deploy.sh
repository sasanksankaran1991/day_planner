#!/usr/bin/env bash
# Build + deploy everything. Usage (from repo root): bash scripts/gcp/deploy.sh
#
# Prerequisites:
#   1. cp scripts/gcp/config.env.example scripts/gcp/config.env  (edit project id)
#   2. Secrets already in Secret Manager (Console) — no .env, no prompts
#   3. bash scripts/gcp/bootstrap.sh  (first time only)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID"

require_secrets
grant_secret_access
build_images

prefix="$(image_prefix)"
deploy_service day-planner-ui "${prefix}-streamlit"
deploy_service day-planner-jobs "${prefix}-jobs"
deploy_service day-planner-bot "${prefix}-planner-bot"
deploy_service day-planner-todo-bot "${prefix}-todo-bot"

init_database
setup_scheduler

ui_url="$(gcloud run services describe day-planner-ui \
  --region "$GCP_REGION" --project "$GCP_PROJECT_ID" \
  --format='value(status.url)')"

echo ""
log "Deployment complete."
echo "  Streamlit:  ${ui_url}"
echo "  Secrets:    Secret Manager (no .env on server)"
echo ""
echo "Next: open the URL, log in, link both Telegram bots in Settings."
