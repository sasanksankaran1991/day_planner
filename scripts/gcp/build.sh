#!/usr/bin/env bash
# Build and push Docker image. Usage: bash scripts/gcp/build.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/gcp/_lib.sh"

require_gcloud
load_config

gcloud config set project "$GCP_PROJECT_ID"
build_image
log "Image: $(image_uri)"
