# Secret Manager only (no .env on server)

Production uses **Google Secret Manager** for all sensitive values. You do **not** need a `.env` file on your server.

## Secret names in GCP

| Secret Manager id | Used for |
|-------------------|----------|
| `day-planner-telegram-bot-token` | Planner Telegram bot |
| `day-planner-telegram-bot-username` | Planner bot @username |
| `day-planner-todo-telegram-bot-token` | Todos Telegram bot |
| `day-planner-todo-telegram-bot-username` | Todos bot @username |
| `day-planner-admin-username` | Web app admin login |
| `day-planner-admin-password` | Web app admin password |
| `day-planner-scheduler-secret` | Cloud Scheduler auth header |

## Option A — Interactive script (easiest on server)

```bash
export GCP_PROJECT_ID=dayplannerserver
chmod +x deploy/create-secrets.sh
./deploy/create-secrets.sh
```

You will be prompted for each value. Passwords are hidden as you type.

## Option B — Export values inline (no prompts, no .env file)

```bash
export GCP_PROJECT_ID=dayplannerserver
export TELEGRAM_BOT_TOKEN='your-token'
export TELEGRAM_BOT_USERNAME='your_planner_bot'
export TODO_TELEGRAM_BOT_TOKEN='your-todo-token'
export TODO_TELEGRAM_BOT_USERNAME='your_todo_bot'
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='your-strong-password'
export SCHEDULER_SECRET="$(openssl rand -hex 32)"

./deploy/create-secrets.sh
```

## Option C — Google Cloud Console (manual)

1. Open [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=dayplannerserver)
2. Click **Create secret** for each id in the table above
3. Paste the value and save

## Option D — gcloud one-by-one

```bash
export GCP_PROJECT_ID=dayplannerserver

printf '%s' 'YOUR_TOKEN' | gcloud secrets create day-planner-telegram-bot-token \
  --project="$GCP_PROJECT_ID" --replication-policy=automatic --data-file=-

# Repeat for each secret, or use versions add if secret already exists:
printf '%s' 'NEW_VALUE' | gcloud secrets versions add day-planner-telegram-bot-token \
  --project="$GCP_PROJECT_ID" --data-file=-
```

## Verify secrets exist

```bash
gcloud secrets list --project=dayplannerserver
```

## Deploy (no .env needed)

```bash
export GCP_PROJECT_ID=dayplannerserver
export GCP_REGION=asia-south1

./deploy/cloud-run-deploy.sh
```

Cloud Run sets `USE_SECRET_MANAGER=true` automatically. Services read secrets at startup.

## Update a single secret later

```bash
printf '%s' 'NEW_PASSWORD' | gcloud secrets versions add day-planner-admin-password \
  --project=dayplannerserver --data-file=-
```

Redeploy or restart Cloud Run services to pick up the new version.
