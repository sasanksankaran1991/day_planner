#!/usr/bin/env bash
# Full first-time setup + deploy (like individual_ikr).
# Usage (from repo root): bash scripts/gcp/setup-and-deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [[ ! -f "$ROOT/scripts/gcp/config.env" ]]; then
  cp "$ROOT/scripts/gcp/config.env.example" "$ROOT/scripts/gcp/config.env"
  echo "Created scripts/gcp/config.env — edit GCP_PROJECT_ID and re-run." >&2
  exit 1
fi

bash "$ROOT/scripts/gcp/bootstrap.sh"
echo ""
echo "Ensure all 7 secrets have values in Secret Manager:"
echo "  https://console.cloud.google.com/security/secret-manager?project=$(grep '^GCP_PROJECT_ID=' "$ROOT/scripts/gcp/config.env" | cut -d= -f2)"
echo ""

bash "$ROOT/scripts/gcp/deploy.sh"
