# GCP deploy

Production config is committed: **`scripts/gcp/config.env`** (no secrets — those are in Secret Manager).

## After git pull

```bash
cd day_planner
git pull origin main
bash scripts/gcp/deploy.sh
```

## First time only

```bash
bash scripts/gcp/bootstrap.sh
bash scripts/gcp/deploy.sh
```

Or one command: `bash scripts/gcp/setup-and-deploy.sh`

## Custom domain

```bash
bash scripts/gcp/map-domain.sh
```

GoDaddy CNAME: `planner` → `ghs.googlehosted.com`

## Status

```bash
bash scripts/gcp/status.sh
```

## Config reference (`scripts/gcp/config.env`)

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | dayplannerserver |
| `GCP_REGION` | asia-southeast1 (Singapore) |
| `GCS_DATA_BUCKET` | dayplannerserver-dp-data-sg (Singapore) |

## Move DB bucket to Singapore (fix latency)

If Cloud Run is in `asia-southeast1` but the bucket was created in Mumbai:

```bash
# config.env should use GCS_DATA_BUCKET=dayplannerserver-dp-data-sg
bash scripts/gcp/bootstrap.sh
bash scripts/gcp/migrate-bucket.sh dayplannerserver-dp-data
bash scripts/gcp/deploy.sh
```
| `DOMAIN` | planner.sasanksankaran.in |
| `STREAMLIT_PUBLIC` | 1 |
