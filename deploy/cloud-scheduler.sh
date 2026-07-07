#!/usr/bin/env bash
# Create Google Cloud Scheduler jobs that POST to the jobs service.
#
# Cloud Scheduler minimum interval is 1 minute. Notification logic inside
# each job already checks the exact minute / hour per user timezone.
#
# Usage:
#   export GCP_PROJECT_ID=your-project
#   export GCP_REGION=asia-south1
#   export JOBS_SERVICE_URL=https://day-planner-jobs-xxxxx.run.app
#   ./deploy/cloud-scheduler.sh
#
# SCHEDULER_SECRET is read from Secret Manager (day-planner-scheduler-secret)
# unless you export SCHEDULER_SECRET explicitly.
#
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_REGION:=asia-south1}"
: "${JOBS_SERVICE_URL:?Set JOBS_SERVICE_URL}"

if [[ -z "${SCHEDULER_SECRET:-}" ]]; then
  SCHEDULER_SECRET="$(gcloud secrets versions access latest \
    --secret=day-planner-scheduler-secret \
    --project="$GCP_PROJECT_ID")"
fi

: "${SCHEDULER_SECRET:?Set SCHEDULER_SECRET or create day-planner-scheduler-secret}"

SCHEDULE="* * * * *"
TIME_ZONE="Asia/Kolkata"

create_job() {
  local job_name="$1"
  local path="$2"

  gcloud scheduler jobs delete "$job_name" --location "$GCP_REGION" --quiet 2>/dev/null || true

  gcloud scheduler jobs create http "$job_name" \
    --location "$GCP_REGION" \
    --schedule "$SCHEDULE" \
    --time-zone "$TIME_ZONE" \
    --uri "${JOBS_SERVICE_URL}${path}" \
    --http-method POST \
    --headers "X-Scheduler-Secret=${SCHEDULER_SECRET},Content-Type=application/json" \
    --attempt-deadline 120s
}

create_job "planner-block-starts" "/jobs/planner/block-starts"
create_job "planner-day-summaries" "/jobs/planner/day-summaries"
create_job "todo-morning" "/jobs/todo/morning"
create_job "todo-reminders" "/jobs/todo/reminders"
create_job "todo-task-end" "/jobs/todo/task-end"

echo "Cloud Scheduler jobs created (every minute)."
