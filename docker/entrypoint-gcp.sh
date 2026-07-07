#!/bin/sh
# Streamlit: pull DB on start (+ optional periodic refresh).
# Jobs: pull only after acquiring the writer lock in Python (job_db_session).
set -e

if [ -n "$GCS_DATA_BUCKET" ] && [ "${1:-}" = "streamlit" ]; then
  echo "GCS sync: pulling from gs://${GCS_DATA_BUCKET}/ ..."
  if ! python /app/scripts/gcp/gcs_pull_safe.py; then
    echo "GCS sync pull failed (check GCS_DATA_BUCKET and runner SA storage access)." >&2
  fi

  if [ -n "${GCS_SYNC_INTERVAL_SEC:-}" ]; then
    (
      while true; do
        sleep "$GCS_SYNC_INTERVAL_SEC"
        python /app/scripts/gcp/gcs_pull_safe.py || true
      done
    ) &
  fi
fi

exec "$@"
