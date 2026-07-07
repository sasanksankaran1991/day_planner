#!/usr/bin/env bash
# Map a custom domain to the day-planner-ui Cloud Run service.
# Usage (from repo root): bash scripts/gcp/map-domain.sh
#   DOMAIN=planner.sasanksankaran.in bash scripts/gcp/map-domain.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

DOMAIN="${DOMAIN:-planner.sasanksankaran.in}"
SERVICE="${DP_STREAMLIT_SERVICE:-day-planner-ui}"
REGION="$GCP_REGION"
PROJECT="$GCP_PROJECT_ID"

gcloud config set project "$PROJECT"

log "Mapping $DOMAIN → $SERVICE ($REGION, $PROJECT)"

if gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$REGION" &>/dev/null; then
  log "Domain mapping already exists:"
  gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$REGION"
else
  gcloud beta run domain-mappings create \
    --service="$SERVICE" \
    --domain="$DOMAIN" \
    --region="$REGION" \
    --project="$PROJECT"
fi

echo ""
log "DNS records required (add at your DNS provider for sasanksankaran.in):"
gcloud beta run domain-mappings describe \
  --domain="$DOMAIN" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format='yaml(status.resourceRecords)'

echo ""
echo "GoDaddy → sasanksankaran.in → DNS → Add record:"
echo "  Type:  CNAME"
echo "  Name:  planner"
echo "  Value: ghs.googlehosted.com   (use exact target from GCP output above if different)"
echo ""
echo "If GCP shows a TXT record for verification, add that too."
echo ""
echo "After DNS propagates (15 min – 2 hours), open: https://${DOMAIN}"
echo ""
echo "Ensure STREAMLIT_PUBLIC=1 in scripts/gcp/config.env, then: bash scripts/gcp/deploy.sh"
