#!/usr/bin/env bash
# Day Planner — Mac / Linux launcher
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python run.py "$@"
fi

exec python3 run.py "$@"
