#!/usr/bin/env bash
# Copy Day Planner data from an old GCS bucket (e.g. Mumbai) into the bucket
# named in scripts/gcp/config.env (Singapore).
#
# Usage (from repo root):
#   bash scripts/gcp/migrate-bucket.sh [OLD_BUCKET]
#
# Example:
#   bash scripts/gcp/migrate-bucket.sh dayplannerserver-dp-data

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

OLD_BUCKET="${1:-dayplannerserver-dp-data}"
NEW_BUCKET="$GCS_DATA_BUCKET"

if [[ "$OLD_BUCKET" == "$NEW_BUCKET" ]]; then
  echo "Old and new bucket names are the same: $OLD_BUCKET" >&2
  exit 1
fi

if ! gcloud storage buckets describe "gs://${OLD_BUCKET}" &>/dev/null; then
  echo "Old bucket not found: gs://${OLD_BUCKET}" >&2
  exit 1
fi

if ! gcloud storage buckets describe "gs://${NEW_BUCKET}" &>/dev/null; then
  echo "New bucket not found: gs://${NEW_BUCKET}" >&2
  echo "Run: bash scripts/gcp/bootstrap.sh" >&2
  exit 1
fi

OLD_LOC="$(gcloud storage buckets describe "gs://${OLD_BUCKET}" --format='value(location)')"
NEW_LOC="$(gcloud storage buckets describe "gs://${NEW_BUCKET}" --format='value(location)')"

log "Copying gs://${OLD_BUCKET} (${OLD_LOC}) -> gs://${NEW_BUCKET} (${NEW_LOC})"

gcloud storage cp -r "gs://${OLD_BUCKET}/*" "gs://${NEW_BUCKET}/"

log "Copy complete."
echo ""
echo "Next:"
echo "  bash scripts/gcp/deploy.sh"
echo "  gcloud run jobs execute dp-sync-admin --region=${GCP_REGION} --wait"
echo ""
echo "After verifying the app, you may delete the old bucket:"
echo "  gcloud storage rm -r gs://${OLD_BUCKET}"
