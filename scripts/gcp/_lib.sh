#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

REQUIRED_SECRETS=(
  day-planner-telegram-bot-token
  day-planner-telegram-bot-username
  day-planner-todo-telegram-bot-token
  day-planner-todo-telegram-bot-username
  day-planner-admin-username
  day-planner-admin-password
)

require_gcloud() {
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install" >&2
    exit 1
  fi
}

load_config() {
  CONFIG_FILE="${CONFIG_FILE:-$ROOT/scripts/gcp/config.env}"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Missing $CONFIG_FILE" >&2
    echo "  cp scripts/gcp/config.env.example scripts/gcp/config.env" >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source <(sed 's/\r$//' "$CONFIG_FILE")
  : "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID in config.env}"
  : "${GCP_REGION:?Set GCP_REGION in config.env}"
  GCS_DATA_BUCKET="${GCS_DATA_BUCKET:-${GCP_PROJECT_ID}-dp-data}"
  AR_REPO="${AR_REPO:-day-planner}"
  DP_IMAGE="${DP_IMAGE:-day-planner}"
  RUNNER_SA="${RUNNER_SA:-dp-runner}"
  SCHEDULER_SA="${SCHEDULER_SA:-dp-scheduler}"
  USE_SECRET_MANAGER="${USE_SECRET_MANAGER:-1}"
  TZ="${TZ:-Asia/Kolkata}"
  STREAMLIT_PUBLIC="${STREAMLIT_PUBLIC:-1}"
  STREAMLIT_MIN_INSTANCES="${STREAMLIT_MIN_INSTANCES:-0}"
  GCS_SYNC_INTERVAL_SEC="${GCS_SYNC_INTERVAL_SEC:-300}"
  GCS_DB_LOCK_WAIT_SEC="${GCS_DB_LOCK_WAIT_SEC:-600}"
  GCS_DB_LOCK_POLL_SEC="${GCS_DB_LOCK_POLL_SEC:-3}"
  GCS_DB_LOCK_TTL_SEC="${GCS_DB_LOCK_TTL_SEC:-900}"
  GCS_DB_LOCK_UI_POLL_SEC="${GCS_DB_LOCK_UI_POLL_SEC:-0.5}"
  GCS_UI_PRIORITY_TTL_SEC="${GCS_UI_PRIORITY_TTL_SEC:-30}"
  DOMAIN="${DOMAIN:-planner.sasanksankaran.in}"
  DP_STREAMLIT_SERVICE="${DP_STREAMLIT_SERVICE:-day-planner-ui}"
}

log() {
  echo "==> $*"
}

image_uri() {
  echo "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO}/${DP_IMAGE}:latest"
}

runner_sa_email() {
  echo "${RUNNER_SA}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
}

scheduler_sa_email() {
  echo "${SCHEDULER_SA}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
}

common_env() {
  printf 'GOOGLE_CLOUD_PROJECT=%s,USE_SECRET_MANAGER=true,USE_CLOUD_SCHEDULER=1,GCP_PROJECT_ID=%s,GCS_DATA_BUCKET=%s,TZ=%s,GCP_REGION=%s,GCS_DB_LOCK_WAIT_SEC=%s,GCS_DB_LOCK_POLL_SEC=%s,GCS_DB_LOCK_TTL_SEC=%s,GCS_DB_LOCK_UI_POLL_SEC=%s,GCS_UI_PRIORITY_TTL_SEC=%s' \
    "$GCP_PROJECT_ID" "$GCP_PROJECT_ID" "$GCS_DATA_BUCKET" "$TZ" "$GCP_REGION" \
    "${GCS_DB_LOCK_WAIT_SEC}" "${GCS_DB_LOCK_POLL_SEC}" "${GCS_DB_LOCK_TTL_SEC}" \
    "${GCS_DB_LOCK_UI_POLL_SEC}" "${GCS_UI_PRIORITY_TTL_SEC}"
}

secret_exists() {
  gcloud secrets describe "$1" --project="$GCP_PROJECT_ID" >/dev/null 2>&1
}

require_secrets() {
  local missing=()
  local secret_id

  for secret_id in "${REQUIRED_SECRETS[@]}"; do
    if ! secret_exists "$secret_id"; then
      missing+=("$secret_id")
    fi
  done

  if ((${#missing[@]} > 0)); then
    echo "Missing secrets in Secret Manager:" >&2
    for secret_id in "${missing[@]}"; do
      echo "  - $secret_id" >&2
    done
    exit 1
  fi

  log "All ${#REQUIRED_SECRETS[@]} secrets found in Secret Manager."
}

require_bootstrap() {
  if ! gcloud artifacts repositories describe "$AR_REPO" \
    --location="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo "" >&2
    echo "Artifact Registry repo '$AR_REPO' not found." >&2
    echo "Run first: bash scripts/gcp/bootstrap.sh" >&2
    exit 1
  fi

  if ! gcloud storage buckets describe "gs://${GCS_DATA_BUCKET}" &>/dev/null; then
    echo "" >&2
    echo "GCS bucket 'gs://${GCS_DATA_BUCKET}' not found." >&2
    echo "Run first: bash scripts/gcp/bootstrap.sh" >&2
    exit 1
  fi

  if ! gcloud iam service-accounts describe "$(runner_sa_email)" \
    --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo "" >&2
    echo "Service account $(runner_sa_email) not found." >&2
    echo "Run first: bash scripts/gcp/bootstrap.sh" >&2
    exit 1
  fi
}

build_image() {
  log "Building image $(image_uri)..."
  gcloud builds submit "$ROOT" \
    --project "$GCP_PROJECT_ID" \
    --config "$ROOT/cloudbuild.yaml" \
    --substitutions="_IMAGE=$(image_uri)" \
    --quiet
}

deploy_streamlit_service() {
  local img auth_flag
  img="$(image_uri)"
  auth_flag="--no-allow-unauthenticated"

  if [[ "${STREAMLIT_PUBLIC}" == "1" ]]; then
    auth_flag="--allow-unauthenticated"
  fi

  log "Cloud Run service: day-planner-ui (only always-on service)"
  # shellcheck disable=SC2086
  gcloud run deploy day-planner-ui \
    --image="$img" \
    --region="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --service-account="$(runner_sa_email)" \
    --set-env-vars="$(common_env),GCS_SYNC_INTERVAL_SEC=${GCS_SYNC_INTERVAL_SEC}" \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances="${STREAMLIT_MIN_INSTANCES}" \
    --max-instances=1 \
    --timeout=3600 \
    --command=/entrypoint-gcp.sh \
    --args="streamlit,run,app.py,--server.port=8080,--server.address=0.0.0.0,--server.headless=true" \
    $auth_flag \
    --quiet
}

deploy_job() {
  local job_name="$1"
  local script_path="$2"
  local img
  img="$(image_uri)"

  log "Cloud Run Job: ${job_name}"
  local -a flags=(
    --image="$img"
    --region="$GCP_REGION"
    --project="$GCP_PROJECT_ID"
    --service-account="$(runner_sa_email)"
    --set-env-vars="$(common_env)"
    --command=/entrypoint-gcp.sh
    --args="python,${script_path}"
    --max-retries=1
    --task-timeout=15m
    --memory=512Mi
    --cpu=1
    --quiet
  )

  if gcloud run jobs describe "$job_name" --region="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
    gcloud run jobs update "$job_name" "${flags[@]}"
  else
    gcloud run jobs create "$job_name" "${flags[@]}"
  fi

  gcloud run jobs add-iam-policy-binding "$job_name" \
    --region="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --member="serviceAccount:$(scheduler_sa_email)" \
    --role="roles/run.invoker" \
    --quiet >/dev/null
}

schedule_job() {
  local sched_name="$1"
  local cron="$2"
  local job_name="$3"
  local uri="https://${GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT_ID}/jobs/${job_name}:run"

  log "Cloud Scheduler: ${sched_name} (${cron})"
  if gcloud scheduler jobs describe "$sched_name" --location="$GCP_REGION" &>/dev/null; then
    gcloud scheduler jobs update http "$sched_name" \
      --location="$GCP_REGION" \
      --schedule="$cron" \
      --uri="$uri" \
      --http-method=POST \
      --oauth-service-account-email="$(scheduler_sa_email)" \
      --time-zone="$TZ" \
      --quiet
  else
    gcloud scheduler jobs create http "$sched_name" \
      --location="$GCP_REGION" \
      --schedule="$cron" \
      --uri="$uri" \
      --http-method=POST \
      --oauth-service-account-email="$(scheduler_sa_email)" \
      --time-zone="$TZ" \
      --quiet
  fi
}

deploy_all_jobs() {
  deploy_job dp-init-db scripts/init_db.py
  deploy_job dp-sync-admin scripts/sync_admin_from_secrets.py
  deploy_job dp-planner-telegram-poll scripts/run_planner_telegram_poll.py
  deploy_job dp-todo-telegram-poll scripts/run_todo_telegram_poll.py
  deploy_job dp-notifications-tick scripts/run_notifications_tick.py
}

setup_schedulers() {
  schedule_job dp-planner-telegram-poll-schedule "*/2 * * * *" dp-planner-telegram-poll
  schedule_job dp-todo-telegram-poll-schedule "*/2 * * * *" dp-todo-telegram-poll
  schedule_job dp-notifications-tick-schedule "* * * * *" dp-notifications-tick
}

retire_legacy_services() {
  for svc in day-planner-jobs day-planner-bot day-planner-todo-bot; do
    if gcloud run services describe "$svc" --region="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
      log "Deleting legacy service: $svc (replaced by Cloud Run Jobs)"
      gcloud run services delete "$svc" --region="$GCP_REGION" --project="$GCP_PROJECT_ID" --quiet || true
    fi
  done
}

init_database() {
  sync_admin_on_deploy
}

sync_admin_on_deploy() {
  local admin_user tmp_db
  admin_user="$(gcloud secrets versions access latest \
    --secret=day-planner-admin-username \
    --project="$GCP_PROJECT_ID" | tr -d '\r\n')"

  log "Syncing admin user '${admin_user}' from Secret Manager into GCS database..."

  if ! gcloud run jobs describe dp-sync-admin \
    --region="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo "Cloud Run job dp-sync-admin not found. deploy_all_jobs should create it." >&2
    exit 1
  fi

  if ! gcloud run jobs execute dp-sync-admin \
    --region="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --wait; then
    echo "dp-sync-admin failed. Check Cloud Run job logs in Console." >&2
    exit 1
  fi

  if ! gcloud storage ls "gs://${GCS_DATA_BUCKET}/day_planner.db" &>/dev/null; then
    log "No database in GCS yet — running dp-init-db..."
    gcloud run jobs execute dp-init-db \
      --region="$GCP_REGION" \
      --project="$GCP_PROJECT_ID" \
      --wait
    gcloud run jobs execute dp-sync-admin \
      --region="$GCP_REGION" \
      --project="$GCP_PROJECT_ID" \
      --wait
  fi

  if gcloud storage ls "gs://${GCS_DATA_BUCKET}/day_planner.db" &>/dev/null; then
    tmp_db="$(mktemp)"
    gcloud storage cp "gs://${GCS_DATA_BUCKET}/day_planner.db" "$tmp_db" --quiet
    if sqlite3 "$tmp_db" \
      "SELECT 1 FROM users WHERE username='${admin_user}' AND is_active=1 LIMIT 1;" \
      | grep -q 1; then
      log "Admin '${admin_user}' verified in gs://${GCS_DATA_BUCKET}/day_planner.db"
    else
      echo "" >&2
      echo "WARNING: Admin '${admin_user}' not found in GCS database after sync." >&2
      echo "Re-running init + sync..." >&2
      gcloud run jobs execute dp-init-db \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --wait
      gcloud run jobs execute dp-sync-admin \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --wait
    fi
    rm -f "$tmp_db"
  fi

  echo ""
  log "Admin login (from Secret Manager):"
  echo "  Username: ${admin_user}"
  echo "  Password: day-planner-admin-password (GCP Console → Secret Manager)"
}

print_status() {
  echo ""
  log "=== Cloud Run SERVICES (should be 1: day-planner-ui) ==="
  gcloud run services list \
    --region="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="table(SERVICE,REGION,URL,LAST_DEPLOYED_BY)"

  echo ""
  log "=== Cloud Run JOBS (should be 4) ==="
  gcloud run jobs list \
    --region="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="table(JOB,REGION,LAST_RUN_AT)"

  echo ""
  log "=== Cloud Scheduler (should be 3) ==="
  gcloud scheduler jobs list \
    --location="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="table(ID,SCHEDULE,TARGET_TYPE,STATE)" 2>/dev/null || \
    echo "(none — run bootstrap + deploy)"
}
