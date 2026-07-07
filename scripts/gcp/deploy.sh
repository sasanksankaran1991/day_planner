#!/usr/bin/env bash
# Deploy Day Planner like individual_ikr:
#   - Only Streamlit runs as a Cloud Run SERVICE (scales to zero)
#   - Telegram poll + notifications run as Cloud Run JOBS on a schedule
#
# Usage (from repo root): bash scripts/gcp/deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID"

require_secrets
require_bootstrap
build_image
deploy_streamlit_service
deploy_all_jobs
init_database
setup_schedulers
retire_legacy_services

ui_url="$(gcloud run services describe day-planner-ui \
  --region "$GCP_REGION" --project "$GCP_PROJECT_ID" \
  --format='value(status.url)')"

echo ""
log "Deployment complete."
echo "  Streamlit (only service): ${ui_url}"
echo "  Image:                    $(image_uri)"
echo "  Telegram poll jobs:       every 2 min"
echo "  Notification job:         every 1 min"
echo "  DB storage:               gs://${GCS_DATA_BUCKET}/day_planner.db"
echo ""
echo "Legacy day-planner-bot, day-planner-todo-bot, day-planner-jobs removed."
echo "Next: open the URL, log in, link both Telegram bots."

print_status
