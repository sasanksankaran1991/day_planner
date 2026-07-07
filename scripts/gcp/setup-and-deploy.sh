#!/usr/bin/env bash
# Full first-time setup + deploy.
# Usage (from repo root): bash scripts/gcp/setup-and-deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [[ ! -f "$ROOT/scripts/gcp/config.env" ]]; then
  cp "$ROOT/scripts/gcp/config.env.example" "$ROOT/scripts/gcp/config.env"
fi

bash "$ROOT/scripts/gcp/bootstrap.sh"
bash "$ROOT/scripts/gcp/deploy.sh"
