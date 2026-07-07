#!/usr/bin/env bash
# Show admin username from Secret Manager (password is never printed).
# Usage: bash scripts/gcp/admin-login-hint.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID" --quiet

admin_user="$(gcloud secrets versions access latest \
  --secret=day-planner-admin-username \
  --project="$GCP_PROJECT_ID")"

echo "Log in at your Streamlit URL with:"
echo "  Username: ${admin_user}"
echo "  Password: (value stored in Secret Manager: day-planner-admin-password)"
echo ""
echo "View password in Console:"
echo "  https://console.cloud.google.com/security/secret-manager/day-planner-admin-password?project=${GCP_PROJECT_ID}"
