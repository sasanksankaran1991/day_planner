#!/usr/bin/env bash
# Deploy Day Planner services to Google Cloud Run.
#
# Prerequisites:
#   gcloud auth login
#   gcloud config set project YOUR_PROJECT_ID
#   ./deploy/create-secrets.sh   # upload secrets from .env first
#
# Usage:
#   export GCP_PROJECT_ID=your-project
#   export GCP_REGION=asia-south1
#   ./deploy/cloud-run-deploy.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_REGION:=asia-south1}"

IMAGE_PREFIX="gcr.io/${GCP_PROJECT_ID}/day-planner"

PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Secret Manager access to ${RUNTIME_SA}..."
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  >/dev/null

build_image() {
  local image="$1"
  local dockerfile="$2"

  gcloud builds submit . \
    --project "$GCP_PROJECT_ID" \
    --config deploy/cloudbuild.yaml \
    --substitutions="_IMAGE=${image},_DOCKERFILE=${dockerfile}"
}

echo "Building images..."
build_image "${IMAGE_PREFIX}-streamlit" "deploy/Dockerfile.streamlit"
build_image "${IMAGE_PREFIX}-jobs" "deploy/Dockerfile.jobs"
build_image "${IMAGE_PREFIX}-planner-bot" "deploy/Dockerfile.planner-bot"
build_image "${IMAGE_PREFIX}-todo-bot" "deploy/Dockerfile.todo-bot"

COMMON_ENV="USE_SECRET_MANAGER=true,USE_CLOUD_SCHEDULER=true,GCP_PROJECT_ID=${GCP_PROJECT_ID}"

deploy_service() {
  local name="$1"
  local image="$2"
  local extra_args="${3:-}"

  gcloud run deploy "$name" \
    --image "$image" \
    --region "$GCP_REGION" \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 1 \
    --memory 512Mi \
    --set-env-vars "${COMMON_ENV}" \
    $extra_args
}

echo "Deploying Cloud Run services..."
deploy_service "day-planner-ui" "${IMAGE_PREFIX}-streamlit"
deploy_service "day-planner-jobs" "${IMAGE_PREFIX}-jobs"
deploy_service "day-planner-bot" "${IMAGE_PREFIX}-planner-bot"
deploy_service "day-planner-todo-bot" "${IMAGE_PREFIX}-todo-bot"

JOBS_URL="$(gcloud run services describe day-planner-jobs --region "$GCP_REGION" --format='value(status.url)')"

echo ""
echo "Jobs service URL: ${JOBS_URL}"
echo "Run ./deploy/cloud-scheduler.sh with JOBS_SERVICE_URL=${JOBS_URL}"
