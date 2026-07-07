# Google Cloud deployment

Day Planner runs as **four Cloud Run services** plus **Cloud Scheduler** HTTP jobs.

| Service | Role |
|---------|------|
| `day-planner-ui` | Streamlit web app |
| `day-planner-jobs` | Notification job HTTP API (Cloud Scheduler target) |
| `day-planner-bot` | Planner Telegram bot (messages only) |
| `day-planner-todo-bot` | Todos Telegram bot (messages only) |

## Architecture

```
Cloud Scheduler (every 1 min)
        │ POST + X-Scheduler-Secret
        ▼
day-planner-jobs  ──► Telegram APIs (send photos)
        ▲
        │ shared SQLite / Cloud SQL
day-planner-ui, bots
```

**Local dev (default):** `USE_SECRET_MANAGER=false` — tokens and admin credentials load from `.env`.

**GCP:** `USE_SECRET_MANAGER=true` (auto-enabled on Cloud Run) — all sensitive values are fetched from **Google Secret Manager** at startup.

**Local dev scheduler:** `USE_CLOUD_SCHEDULER=false` — bots run all notification jobs every **5 seconds** internally.

**GCP scheduler:** `USE_CLOUD_SCHEDULER=true` — bots only handle `/create`, Done/Skip, etc. Cloud Scheduler triggers the jobs service every **minute** (GCP minimum; job logic already checks exact minute/hour).

**Local GCP simulation:** run jobs server + `scripts/run_local_scheduler.py` (5s tick) with `USE_CLOUD_SCHEDULER=true` on bots.

## Prerequisites

- Google Cloud project with billing enabled
- APIs: Cloud Run, Cloud Build, Cloud Scheduler, **Secret Manager**
- `gcloud` CLI authenticated

## 1. Upload secrets

Fill `.env` locally, then upload to Secret Manager:

```bash
export GCP_PROJECT_ID=your-project-id
chmod +x deploy/create-secrets.sh
./deploy/create-secrets.sh
```

| Secret id | Maps to |
|-----------|---------|
| `day-planner-telegram-bot-token` | `TELEGRAM_BOT_TOKEN` |
| `day-planner-telegram-bot-username` | `TELEGRAM_BOT_USERNAME` |
| `day-planner-todo-telegram-bot-token` | `TODO_TELEGRAM_BOT_TOKEN` |
| `day-planner-todo-telegram-bot-username` | `TODO_TELEGRAM_BOT_USERNAME` |
| `day-planner-admin-username` | `ADMIN_USERNAME` |
| `day-planner-admin-password` | `ADMIN_PASSWORD` |
| `day-planner-scheduler-secret` | `SCHEDULER_SECRET` |

Generate a scheduler secret before upload:

```bash
export SCHEDULER_SECRET=$(openssl rand -hex 32)
# add to .env, then run create-secrets.sh
```

## 2. Deploy Cloud Run services

```bash
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=asia-south1
chmod +x deploy/cloud-run-deploy.sh
./deploy/cloud-run-deploy.sh
```

The deploy script grants `roles/secretmanager.secretAccessor` to the Cloud Run runtime service account and sets `USE_SECRET_MANAGER=true`.

## 3. Create Cloud Scheduler jobs

```bash
export JOBS_SERVICE_URL=$(gcloud run services describe day-planner-jobs \
  --region "$GCP_REGION" --format='value(status.url)')
chmod +x deploy/cloud-scheduler.sh
./deploy/cloud-scheduler.sh
```

`cloud-scheduler.sh` reads `SCHEDULER_SECRET` from Secret Manager automatically.

Jobs created (all `* * * * *` — every minute):

| Job | Endpoint |
|-----|----------|
| planner-block-starts | `/jobs/planner/block-starts` |
| planner-day-summaries | `/jobs/planner/day-summaries` |
| todo-morning | `/jobs/todo/morning` |
| todo-reminders | `/jobs/todo/reminders` |
| todo-task-end | `/jobs/todo/task-end` |

## 4. Database on GCP

SQLite works for a **single-instance** prototype. For production, migrate to **Cloud SQL (PostgreSQL)** so Streamlit, jobs, and bots share one database.

Until then, deploy with `min-instances=1` and accept ephemeral storage limits, or mount a persistent volume.

## Local commands

```bash
# Mode A — embedded 5s scheduler in bots (simplest)
USE_SECRET_MANAGER=false
USE_CLOUD_SCHEDULER=false
python scripts/run_bot.py          # terminal 1
python scripts/run_todo_bot.py     # terminal 2
streamlit run app.py               # terminal 3

# Mode B — same as GCP (jobs service + 5s local scheduler)
USE_SECRET_MANAGER=false
USE_CLOUD_SCHEDULER=true
python scripts/run_jobs_server.py  # terminal 1
python scripts/run_local_scheduler.py  # terminal 2
python scripts/run_bot.py          # terminal 3
python scripts/run_todo_bot.py     # terminal 4
streamlit run app.py               # terminal 5
```

## Jobs API (manual test)

```bash
curl -X POST http://localhost:8080/jobs/tick \
  -H "X-Scheduler-Secret: your-secret"
```
