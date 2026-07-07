#!/usr/bin/env bash
# Create or update secrets in Google Cloud Secret Manager.
#
# No .env file required. Secrets can be provided via:
#   1. Exported environment variables (recommended for CI/scripts)
#   2. Interactive prompts (default when values are missing)
#   3. Optional .env file (only if USE_ENV_FILE=true)
#
# Usage:
#   export GCP_PROJECT_ID=dayplannerserver
#   ./deploy/create-secrets.sh
#
# Or pass values inline:
#   GCP_PROJECT_ID=dayplannerserver \
#   TELEGRAM_BOT_TOKEN=... \
#   TELEGRAM_BOT_USERNAME=... \
#   TODO_TELEGRAM_BOT_TOKEN=... \
#   TODO_TELEGRAM_BOT_USERNAME=... \
#   ADMIN_USERNAME=admin \
#   ADMIN_PASSWORD=... \
#   SCHEDULER_SECRET=$(openssl rand -hex 32) \
#   ./deploy/create-secrets.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"

REQUIRED_SECRETS=(
  day-planner-telegram-bot-token
  day-planner-telegram-bot-username
  day-planner-todo-telegram-bot-token
  day-planner-todo-telegram-bot-username
  day-planner-admin-username
  day-planner-admin-password
  day-planner-scheduler-secret
)

secret_exists() {
  gcloud secrets describe "$1" --project "$GCP_PROJECT_ID" >/dev/null 2>&1
}

all_secrets_exist() {
  local secret_id
  for secret_id in "${REQUIRED_SECRETS[@]}"; do
    if ! secret_exists "$secret_id"; then
      return 1
    fi
  done
  return 0
}

if [[ "${FORCE_UPDATE:-false}" != "true" ]] && all_secrets_exist; then
  echo "All ${#REQUIRED_SECRETS[@]} secrets already exist in Secret Manager."
  echo "Nothing to do. Skip this script and run:"
  echo "  export GCP_PROJECT_ID=${GCP_PROJECT_ID}"
  echo "  export GCP_REGION=asia-south1"
  echo "  ./deploy/cloud-run-deploy.sh"
  echo ""
  echo "To overwrite secrets, set FORCE_UPDATE=true or pass values via env vars."
  exit 0
fi

if [[ "${USE_ENV_FILE:-false}" == "true" && -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  echo "Loaded optional values from .env"
fi

prompt_if_empty() {
  local var_name="$1"
  local prompt_text="$2"
  local hidden="${3:-false}"
  local current_value="${!var_name:-}"

  if [[ -n "$current_value" ]]; then
    return
  fi

  if [[ "$hidden" == "true" ]]; then
    read -r -s -p "$prompt_text: " current_value
    echo ""
  else
    read -r -p "$prompt_text: " current_value
  fi

  if [[ -z "$current_value" ]]; then
    echo "Error: ${var_name} is required." >&2
    exit 1
  fi

  printf -v "$var_name" '%s' "$current_value"
}

prompt_if_empty TELEGRAM_BOT_TOKEN "Planner bot token (TELEGRAM_BOT_TOKEN)" true
prompt_if_empty TELEGRAM_BOT_USERNAME "Planner bot username (TELEGRAM_BOT_USERNAME)"
prompt_if_empty TODO_TELEGRAM_BOT_TOKEN "Todos bot token (TODO_TELEGRAM_BOT_TOKEN)" true
prompt_if_empty TODO_TELEGRAM_BOT_USERNAME "Todos bot username (TODO_TELEGRAM_BOT_USERNAME)"
prompt_if_empty ADMIN_USERNAME "Admin username (default: admin)"
prompt_if_empty ADMIN_PASSWORD "Admin password (ADMIN_PASSWORD)" true

ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"

if [[ -z "${SCHEDULER_SECRET:-}" ]]; then
  read -r -s -p "Scheduler secret (press Enter to auto-generate): " SCHEDULER_SECRET || true
  echo ""
fi

if [[ -z "${SCHEDULER_SECRET:-}" ]]; then
  SCHEDULER_SECRET="$(openssl rand -hex 32)"
  echo "Generated SCHEDULER_SECRET."
fi

upsert_secret() {
  local secret_id="$1"
  local secret_value="$2"

  if [[ -z "${secret_value}" ]]; then
    echo "Error: secret value for ${secret_id} is empty." >&2
    exit 1
  fi

  if gcloud secrets describe "$secret_id" --project "$GCP_PROJECT_ID" >/dev/null 2>&1; then
    printf '%s' "$secret_value" | gcloud secrets versions add "$secret_id" \
      --project "$GCP_PROJECT_ID" \
      --data-file=-
    echo "Updated secret: ${secret_id}"
  else
    printf '%s' "$secret_value" | gcloud secrets create "$secret_id" \
      --project "$GCP_PROJECT_ID" \
      --replication-policy="automatic" \
      --data-file=-
    echo "Created secret: ${secret_id}"
  fi
}

echo "Uploading secrets to project ${GCP_PROJECT_ID}..."

upsert_secret "day-planner-telegram-bot-token" "${TELEGRAM_BOT_TOKEN}"
upsert_secret "day-planner-telegram-bot-username" "${TELEGRAM_BOT_USERNAME}"
upsert_secret "day-planner-todo-telegram-bot-token" "${TODO_TELEGRAM_BOT_TOKEN}"
upsert_secret "day-planner-todo-telegram-bot-username" "${TODO_TELEGRAM_BOT_USERNAME}"
upsert_secret "day-planner-admin-username" "${ADMIN_USERNAME}"
upsert_secret "day-planner-admin-password" "${ADMIN_PASSWORD}"
upsert_secret "day-planner-scheduler-secret" "${SCHEDULER_SECRET}"

echo ""
echo "Done. All secrets are in Secret Manager for project ${GCP_PROJECT_ID}."
echo "No .env file is needed on the server or in Cloud Run."
