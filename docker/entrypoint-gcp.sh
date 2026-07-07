#!/bin/sh
# Streamlit: pull DB once on start. Further sync happens inside get_db() on writes.
# Jobs: pull only after acquiring the writer lock in Python (job_db_session).
set -e

if [ -n "$GCS_DATA_BUCKET" ] && [ "${1:-}" = "streamlit" ]; then
  echo "GCS sync: pulling from gs://${GCS_DATA_BUCKET}/ ..."
  if ! python /app/scripts/gcp/gcs_pull_safe.py; then
    echo "GCS sync pull failed (check GCS_DATA_BUCKET and runner SA storage access)." >&2
  fi
fi

exec "$@"
