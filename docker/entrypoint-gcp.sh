#!/bin/sh
# Pull day_planner.db from GCS before a job or Streamlit run.
# Push happens only when Python code actually writes to the DB (not on every exit).
set -e

if [ -n "$GCS_DATA_BUCKET" ]; then
  echo "GCS sync: pulling from gs://${GCS_DATA_BUCKET}/ ..."
  if ! python /app/scripts/gcp/gcs_data_sync.py pull; then
    echo "GCS sync pull failed (check GCS_DATA_BUCKET and runner SA storage access)." >&2
  fi
fi

exec "$@"
