#!/usr/bin/env bash
# Show what is deployed. Usage: bash scripts/gcp/status.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID" --quiet

print_status
