#!/usr/bin/env bash
# Diagnose production issues. Usage: bash scripts/gcp/doctor.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID" --quiet

echo "=========================================="
echo "Day Planner doctor — project: $GCP_PROJECT_ID"
echo "=========================================="

echo ""
echo "1. Cloud Run UI service"
if gcloud run services describe day-planner-ui --region="$GCP_REGION" &>/dev/null; then
  ui_url="$(gcloud run services describe day-planner-ui --region="$GCP_REGION" --format='value(status.url)')"
  echo "   OK  day-planner-ui"
  echo "   URL: $ui_url"
else
  echo "   FAIL  day-planner-ui not found — run: bash scripts/gcp/deploy.sh"
fi

echo ""
echo "2. Custom domain ($DOMAIN)"
if gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$GCP_REGION" &>/dev/null; then
  echo "   OK  domain mapping exists"
  gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$GCP_REGION" \
    --format='table(status.conditions.type,status.conditions.status,status.conditions.message)'
  echo ""
  echo "   DNS records required:"
  gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$GCP_REGION" \
    --format='yaml(status.resourceRecords)'
else
  echo "   FAIL  no domain mapping — run: bash scripts/gcp/map-domain.sh"
  echo "   Then GoDaddy CNAME: planner -> ghs.googlehosted.com"
fi

echo ""
echo "3. GCS database"
if gcloud storage ls "gs://${GCS_DATA_BUCKET}/day_planner.db" &>/dev/null; then
  echo "   OK  gs://${GCS_DATA_BUCKET}/day_planner.db exists"
else
  echo "   FAIL  no database in GCS — run: bash scripts/gcp/deploy.sh"
fi

echo ""
echo "4. Admin credentials (from Secret Manager)"
if secret_exists "day-planner-admin-username" && secret_exists "day-planner-admin-password"; then
  admin_user="$(gcloud secrets versions access latest --secret=day-planner-admin-username --project="$GCP_PROJECT_ID")"
  echo "   OK  username: $admin_user"
  echo "   Password: see Console → day-planner-admin-password"
  echo "   https://console.cloud.google.com/security/secret-manager/day-planner-admin-password?project=${GCP_PROJECT_ID}"
else
  echo "   FAIL  admin secrets missing in Secret Manager"
fi

echo ""
echo "5. Sync admin password into database"
echo "   Run: gcloud run jobs execute dp-sync-admin --region=$GCP_REGION --wait"

echo ""
echo "6. Jobs (should be 4+)"
gcloud run jobs list --region="$GCP_REGION" --format="table(JOB_NAME,REGION)" 2>/dev/null || true

echo ""
echo "7. Schedulers (should be 3)"
gcloud scheduler jobs list --location="$GCP_REGION" --format="table(ID,SCHEDULE,STATE)" 2>/dev/null || true

echo ""
echo "=========================================="
echo "Quick fix sequence:"
echo "  git pull origin main"
echo "  bash scripts/gcp/deploy.sh"
echo "  bash scripts/gcp/map-domain.sh"
echo "  gcloud run jobs execute dp-sync-admin --region=$GCP_REGION --wait"
echo "  Open: https://${DOMAIN}"
echo "=========================================="
