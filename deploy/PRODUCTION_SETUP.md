# Production setup checklist

Use this after pushing code to GitHub.

## Before you start

- [ ] Google Cloud account with billing enabled
- [ ] `gcloud` CLI installed: https://cloud.google.com/sdk/docs/install
- [ ] Git installed (already on macOS)
- [ ] Local `.env` filled with Telegram tokens and admin password
- [ ] **Important:** Cloud Run uses ephemeral storage. Each service gets its own
  SQLite file unless you migrate to Cloud SQL. For a first production test,
  deploy with `min-instances=1` and treat it as a single-user prototype.

## Step 1 — Push code to GitHub

```bash
cd /Users/sasank.sankaran/Desktop/personal/day_planner/day_planner

# Verify secrets are NOT tracked
git status
# .env must NOT appear

git add .
git commit -m "Initial Day Planner release with GCP deployment support."

git remote add origin https://github.com/sasanksankaran1991/day_planner.git
git branch -M main
git push -u origin main
```

If prompted, sign in with your GitHub account or use a Personal Access Token as the password.

## Step 2 — Create a GCP project

```bash
export GCP_PROJECT_ID=day-planner-prod   # pick a unique id
export GCP_REGION=asia-south1

gcloud auth login
gcloud projects create "$GCP_PROJECT_ID"
gcloud config set project "$GCP_PROJECT_ID"
gcloud billing projects link "$GCP_PROJECT_ID" --billing-account=YOUR_BILLING_ACCOUNT_ID
```

Enable required APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

## Step 3 — Upload secrets to Secret Manager

From your project folder (with `.env` present locally only):

```bash
chmod +x deploy/create-secrets.sh
./deploy/create-secrets.sh
```

This uploads:
- Telegram bot tokens/usernames (planner + todos)
- Admin username/password
- Scheduler secret

Generate a strong scheduler secret if needed:

```bash
openssl rand -hex 32
# put result in .env as SCHEDULER_SECRET, then re-run create-secrets.sh
```

## Step 4 — Deploy Cloud Run services

```bash
chmod +x deploy/cloud-run-deploy.sh
./deploy/cloud-run-deploy.sh
```

This builds 4 images and deploys:
| Service | Purpose |
|---------|---------|
| `day-planner-ui` | Streamlit web app |
| `day-planner-jobs` | Notification HTTP API |
| `day-planner-bot` | Planner Telegram bot |
| `day-planner-todo-bot` | Todos Telegram bot |

Get URLs:

```bash
gcloud run services describe day-planner-ui --region "$GCP_REGION" --format='value(status.url)'
gcloud run services describe day-planner-jobs --region "$GCP_REGION" --format='value(status.url)'
```

## Step 5 — Create Cloud Scheduler jobs

```bash
export JOBS_SERVICE_URL=$(gcloud run services describe day-planner-jobs \
  --region "$GCP_REGION" --format='value(status.url)')

chmod +x deploy/cloud-scheduler.sh
./deploy/cloud-scheduler.sh
```

Scheduler hits the jobs service every minute for reminders and summaries.

## Step 6 — Initialize the database on Cloud Run

The UI service needs an initialized DB on first boot. Exec into the running container
or run a one-off Cloud Run job:

```bash
gcloud run jobs create day-planner-init-db \
  --image "gcr.io/${GCP_PROJECT_ID}/day-planner-streamlit" \
  --region "$GCP_REGION" \
  --command python \
  --args scripts/init_db.py \
  --set-env-vars "USE_SECRET_MANAGER=true,GCP_PROJECT_ID=${GCP_PROJECT_ID}"

gcloud run jobs execute day-planner-init-db --region "$GCP_REGION"
```

Open the Streamlit URL and log in with your admin credentials from Secret Manager.

## Step 7 — Link Telegram bots

1. Open Streamlit UI → Account Settings → link **Planner bot**
2. Open Todos → Settings → link **Todos bot**
3. Send `/help` to each bot to confirm they respond

## Step 8 — Verify notifications

```bash
curl -X POST "${JOBS_SERVICE_URL}/jobs/tick" \
  -H "X-Scheduler-Secret: $(gcloud secrets versions access latest --secret=day-planner-scheduler-secret --project=$GCP_PROJECT_ID)"
```

Check Cloud Run logs if anything fails:

```bash
gcloud run services logs read day-planner-jobs --region "$GCP_REGION" --limit 50
gcloud run services logs read day-planner-bot --region "$GCP_REGION" --limit 50
```

## Production hardening (recommended next)

1. **Cloud SQL** — shared PostgreSQL for UI + jobs + bots (SQLite won't sync across services)
2. **Custom domain** — map domain to `day-planner-ui` in Cloud Run
3. **IAM** — remove `--allow-unauthenticated` from jobs service; use Cloud Scheduler OIDC
4. **Backups** — automated DB backups once on Cloud SQL
5. **CI/CD** — GitHub Actions to build/deploy on push to `main`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `gcloud: command not found` | Install Google Cloud SDK |
| Secret Manager permission denied | Re-run `cloud-run-deploy.sh` (grants secretAccessor) |
| Bot not responding | Check `day-planner-bot` logs; confirm token secret is correct |
| No reminders | Confirm Cloud Scheduler jobs exist and `USE_CLOUD_SCHEDULER=true` |
| Data missing after restart | Expected with SQLite on Cloud Run — migrate to Cloud SQL |
