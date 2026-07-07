#!/bin/sh
# Pull day_planner.db from GCS before run.
# - Streamlit: pull on startup only; UI pulls again before each DB write via get_db().
# - Jobs: push on exit after poll/notification ticks (generation-safe).
set -e

if [ -n "$GCS_DATA_BUCKET" ]; then
  echo "GCS sync: pulling from gs://${GCS_DATA_BUCKET}/ ..."
  if ! python /app/scripts/gcp/gcs_data_sync.py pull; then
    echo "GCS sync pull failed (check GCS_DATA_BUCKET and runner SA storage access)." >&2
  fi

  if [ "${1:-}" != "streamlit" ]; then
    trap 'python /app/scripts/gcp/gcs_data_sync.py push || true' EXIT
  fi
fi

exec "$@"
