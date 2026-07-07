# GCP deploy (like individual_ikr)

## Cost-efficient architecture

| Component | Type | Schedule |
|-----------|------|----------|
| `day-planner-ui` | Cloud Run **service** | On demand (min instances = 0) |
| `dp-planner-telegram-poll` | Cloud Run **job** | Every 2 min |
| `dp-todo-telegram-poll` | Cloud Run **job** | Every 2 min |
| `dp-notifications-tick` | Cloud Run **job** | Every 1 min |

No always-on bot services. No HTTP jobs server.

SQLite lives in `gs://YOUR_BUCKET/day_planner.db` and syncs via GCS.

## Quick start

```bash
cp scripts/gcp/config.env.example scripts/gcp/config.env
# edit GCP_PROJECT_ID, GCS_DATA_BUCKET

bash scripts/gcp/bootstrap.sh   # first time only
bash scripts/gcp/deploy.sh
```

Secrets: add values in [Secret Manager Console](https://console.cloud.google.com/security/secret-manager) — no `.env` on server.

## Manual job run

```bash
gcloud run jobs execute dp-planner-telegram-poll --region=asia-south1 --wait
gcloud run jobs execute dp-notifications-tick --region=asia-south1 --wait
```
