#!/usr/bin/env bash
# Create or update secrets in Google Cloud Secret Manager from your local .env.
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   ./deploy/create-secrets.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"

if [[ ! -f .env ]]; then
  echo "Missing .env in ${ROOT_DIR}"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

upsert_secret() {
  local secret_id="$1"
  local secret_value="$2"

  if [[ -z "${secret_value}" ]]; then
    echo "Skipping empty secret: ${secret_id}"
    return
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

upsert_secret "day-planner-telegram-bot-token" "${TELEGRAM_BOT_TOKEN:-}"
upsert_secret "day-planner-telegram-bot-username" "${TELEGRAM_BOT_USERNAME:-}"
upsert_secret "day-planner-todo-telegram-bot-token" "${TODO_TELEGRAM_BOT_TOKEN:-}"
upsert_secret "day-planner-todo-telegram-bot-username" "${TODO_TELEGRAM_BOT_USERNAME:-}"
upsert_secret "day-planner-admin-username" "${ADMIN_USERNAME:-admin}"
upsert_secret "day-planner-admin-password" "${ADMIN_PASSWORD:-}"
upsert_secret "day-planner-scheduler-secret" "${SCHEDULER_SECRET:-}"

echo ""
echo "Secrets uploaded to project ${GCP_PROJECT_ID}."
