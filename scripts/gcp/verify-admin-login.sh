#!/usr/bin/env bash
# Diagnose admin login: checks default admin/admin user in GCS database.
# Usage: bash scripts/gcp/verify-admin-login.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID" --quiet

admin_user="admin"
admin_password="admin"

echo "=== Default admin credentials ==="
echo "Username: ${admin_user}"
echo "Password: ${admin_password}"

echo ""
echo "=== GCS database ==="
tmp="$(mktemp)"
if gcloud storage cp "gs://${GCS_DATA_BUCKET}/day_planner.db" "$tmp" 2>/dev/null; then
  echo "Bucket: gs://${GCS_DATA_BUCKET}/day_planner.db"
  sqlite3 "$tmp" \
    "SELECT id, username, role, is_active FROM users WHERE username='${admin_user}';" \
    || echo "(could not query users table)"
  rm -f "$tmp"
else
  echo "FAIL: no day_planner.db in gs://${GCS_DATA_BUCKET}/"
  echo "Run: gcloud run jobs execute dp-sync-admin --region=${GCP_REGION} --wait"
fi

echo ""
echo "=== Fix ==="
echo "gcloud run jobs execute dp-sync-admin --region=${GCP_REGION} --project=${GCP_PROJECT_ID} --wait"
