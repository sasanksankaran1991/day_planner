#!/bin/sh
# individual_ikr-style GCS sync:
# - Streamlit: pull on start + periodic pull (reads only). Saves push in Python.
# - Jobs: pull on start, push on exit.
set -e

if [ -n "$GCS_DATA_BUCKET" ]; then
  echo "GCS sync: pulling from gs://${GCS_DATA_BUCKET}/ ..."
  if ! python /app/scripts/gcp/gcs_data_sync.py pull; then
    echo "GCS sync pull failed (check GCS_DATA_BUCKET and runner SA storage access)." >&2
  fi

  if [ "${1:-}" = "streamlit" ]; then
    if [ -n "${GCS_SYNC_INTERVAL_SEC:-}" ]; then
      (
        while true; do
          sleep "$GCS_SYNC_INTERVAL_SEC"
          python /app/scripts/gcp/gcs_pull_safe.py || true
        done
      ) &
    fi
  else
    trap 'python /app/scripts/gcp/gcs_data_sync.py push || true' EXIT
  fi
fi

exec "$@"
