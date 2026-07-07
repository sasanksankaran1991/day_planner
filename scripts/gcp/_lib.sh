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
  day-planner-scheduler-secret
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
    echo "  # edit GCP_PROJECT_ID, then re-run" >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source <(sed 's/\r$//' "$CONFIG_FILE")
  : "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID in config.env}"
  : "${GCP_REGION:?Set GCP_REGION in config.env}"
  USE_SECRET_MANAGER="${USE_SECRET_MANAGER:-1}"
  TZ="${TZ:-Asia/Kolkata}"
}

log() {
  echo "==> $*"
}

image_prefix() {
  echo "gcr.io/${GCP_PROJECT_ID}/day-planner"
}

common_env() {
  printf 'USE_SECRET_MANAGER=true,USE_CLOUD_SCHEDULER=true,GCP_PROJECT_ID=%s' "$GCP_PROJECT_ID"
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
    echo "Missing secrets in Secret Manager (add them in Cloud Console):" >&2
    for secret_id in "${missing[@]}"; do
      echo "  - $secret_id" >&2
    done
    echo "" >&2
    echo "https://console.cloud.google.com/security/secret-manager?project=${GCP_PROJECT_ID}" >&2
    exit 1
  fi

  log "All ${#REQUIRED_SECRETS[@]} secrets found in Secret Manager."
}

grant_secret_access() {
  local project_number runtime_sa
  project_number="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
  runtime_sa="${project_number}-compute@developer.gserviceaccount.com"

  log "Granting Secret Manager access to ${runtime_sa}..."
  gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:${runtime_sa}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null
}

build_images() {
  local prefix image dockerfile
  prefix="$(image_prefix)"

  for image_dockerfile in \
    "streamlit:deploy/Dockerfile.streamlit" \
    "jobs:deploy/Dockerfile.jobs" \
    "planner-bot:deploy/Dockerfile.planner-bot" \
    "todo-bot:deploy/Dockerfile.todo-bot"; do
    image="${image_dockerfile%%:*}"
    dockerfile="${image_dockerfile#*:}"
    log "Building ${prefix}-${image}..."
    gcloud builds submit "$ROOT" \
      --project "$GCP_PROJECT_ID" \
      --config "$ROOT/deploy/cloudbuild.yaml" \
      --substitutions="_IMAGE=${prefix}-${image},_DOCKERFILE=${dockerfile}" \
      --quiet
  done
}

deploy_service() {
  local name="$1"
  local image="$2"

  log "Cloud Run service: ${name}"
  gcloud run deploy "$name" \
    --image "$image" \
    --region "$GCP_REGION" \
    --project "$GCP_PROJECT_ID" \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 1 \
    --memory 512Mi \
    --set-env-vars "$(common_env)" \
    --quiet
}

init_database() {
  local prefix image
  prefix="$(image_prefix)"
  image="${prefix}-streamlit"

  log "Cloud Run Job: day-planner-init-db"
  if gcloud run jobs describe day-planner-init-db \
    --region "$GCP_REGION" --project "$GCP_PROJECT_ID" &>/dev/null; then
    gcloud run jobs update day-planner-init-db \
      --image "$image" \
      --region "$GCP_REGION" \
      --project "$GCP_PROJECT_ID" \
      --command python \
      --args scripts/init_db.py \
      --set-env-vars "$(common_env)" \
      --quiet
  else
    gcloud run jobs create day-planner-init-db \
      --image "$image" \
      --region "$GCP_REGION" \
      --project "$GCP_PROJECT_ID" \
      --command python \
      --args scripts/init_db.py \
      --set-env-vars "$(common_env)" \
      --quiet
  fi

  gcloud run jobs execute day-planner-init-db \
    --region "$GCP_REGION" \
    --project "$GCP_PROJECT_ID" \
    --wait
}

setup_scheduler() {
  local jobs_url scheduler_secret
  jobs_url="$(gcloud run services describe day-planner-jobs \
    --region "$GCP_REGION" --project "$GCP_PROJECT_ID" \
    --format='value(status.url)')"

  scheduler_secret="$(gcloud secrets versions access latest \
    --secret=day-planner-scheduler-secret \
    --project="$GCP_PROJECT_ID")"

  create_sched_job() {
    local job_name="$1"
    local path="$2"

    log "Cloud Scheduler: ${job_name}"
    if gcloud scheduler jobs describe "$job_name" \
      --location "$GCP_REGION" &>/dev/null; then
      gcloud scheduler jobs update http "$job_name" \
        --location "$GCP_REGION" \
        --schedule "* * * * *" \
        --time-zone "$TZ" \
        --uri "${jobs_url}${path}" \
        --http-method POST \
        --headers "X-Scheduler-Secret=${scheduler_secret},Content-Type=application/json" \
        --attempt-deadline 120s \
        --quiet
    else
      gcloud scheduler jobs create http "$job_name" \
        --location "$GCP_REGION" \
        --schedule "* * * * *" \
        --time-zone "$TZ" \
        --uri "${jobs_url}${path}" \
        --http-method POST \
        --headers "X-Scheduler-Secret=${scheduler_secret},Content-Type=application/json" \
        --attempt-deadline 120s \
        --quiet
    fi
  }

  create_sched_job planner-block-starts "/jobs/planner/block-starts"
  create_sched_job planner-day-summaries "/jobs/planner/day-summaries"
  create_sched_job todo-morning "/jobs/todo/morning"
  create_sched_job todo-reminders "/jobs/todo/reminders"
  create_sched_job todo-task-end "/jobs/todo/task-end"
}
