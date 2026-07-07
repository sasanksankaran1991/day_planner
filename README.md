# Day Planner

A personal planning app with **scheduled todos** and **hourly day blocks**, built with Streamlit and SQLite. Two Telegram bots provide reminders and quick actions.

## Features

### Todos
- Daily task list with colored ribbons (done, pending, overdue, etc.)
- Repeat: one-time, daily, weekly, weekdays, monthly, or custom days
- Three tabs: Todos, Dashboard, Settings (recurring series management)
- Postpone, done/skip per occurrence; edit series affects future only
- Tags, assignments, achievement dashboard

### Hourly blocks
- Chained time blocks with smart start/end selection
- Edit, insert-between, remove with automatic time adjustments
- Templates, copy yesterday, tags
- Dashboard: streaks and 7-day completion

### Telegram
- **Planner bot** (`scripts/run_bot.py`) — block-start alerts, 5 AM yesterday summary
- **Todos bot** (`scripts/run_todo_bot.py`) — 5 AM summaries, reminders, `/create` tasks

## Quick start (Mac or Windows)

Same steps on both platforms — use **`run.py`** (no bash required). **Python 3.9+** required.

### 1. One-time setup

**Mac / Linux:**
```bash
cd day_planner
python3 -m venv .venv
source .venv/bin/activate
python run.py setup
copy .env.example .env    # then edit .env with your Telegram tokens
```

**Windows (Command Prompt or PowerShell):**
```cmd
cd day_planner
python -m venv .venv
.venv\Scripts\activate
python run.py setup
copy .env.example .env
```

Or double-click **`run.bat setup`** after creating `.venv`.

### 2. Run the web app

```bash
python run.py ui
```

Open http://localhost:8501 — login **`admin`** / **`admin`**.

Data is stored in **`data/day_planner.db`** on your machine (no cloud sync locally).

### 3. Telegram bots (optional, separate terminals)

```bash
python run.py bot        # Day Planner blocks bot
python run.py todo-bot   # Todos bot
```

### Commands

| Command | What it does |
|---------|----------------|
| `python run.py setup` | Install pip packages + create database |
| `python run.py ui` | Streamlit web UI |
| `python run.py bot` | Planner Telegram bot |
| `python run.py todo-bot` | Todos Telegram bot |
| `python run.py init-db` | Re-run migrations + admin user |

**Mac/Linux shortcut:** `./run.sh ui`  
**Windows shortcut:** `run.bat ui`

---

## Quick start (manual, any OS)

```bash
pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
python scripts/setup_local_db.py
streamlit run app.py
```

Default admin login: `admin` / `admin`.

## Project structure

```
day_planner/
├── app.py                 # Streamlit entry point
├── bot/                   # Day Planner Telegram bot
├── todo_bot/              # Todos Telegram bot
├── jobs/                  # Shared notification jobs + HTTP server
├── deploy/                # Dockerfiles + GCP scripts
├── config/settings.py
├── database/              # SQLAlchemy models + SQLite
├── repositories/
├── services/              # Business logic (UI + Telegram)
├── ui/
├── utils/
└── scripts/
```

## Environment variables

See `.env.example`. Never commit `.env` — it holds bot tokens and admin password.

**Local:** `USE_SECRET_MANAGER=false` (default) — sensitive values load from `.env`.

**GCP:** `USE_SECRET_MANAGER=true` — bot tokens, admin credentials, and scheduler secret load from [Google Secret Manager](deploy/README.md#1-upload-secrets).

| Variable | Purpose |
|----------|---------|
| `USE_SECRET_MANAGER` | `false` = `.env`; `true` = Secret Manager |
| `GCP_PROJECT_ID` | GCP project for Secret Manager |
| `TELEGRAM_BOT_TOKEN` | Planner blocks bot |
| `TODO_TELEGRAM_BOT_TOKEN` | Todos bot |
| `DEFAULT_ADMIN_PASSWORD` | Local admin password (default `admin`) |
| `GCS_DATA_BUCKET` | Leave **empty** locally; set only on GCP |
| `USE_CLOUD_SCHEDULER` | `false` = local 5s bot scheduler; `true` = GCP mode |
| `SCHEDULER_SECRET` | Auth header for jobs HTTP API |
| `SCHEDULER_POLL_SECONDS` | Local poll interval (default `5`) |
| `PORT` | HTTP port for jobs service / Cloud Run |

## Google Cloud

See [deploy/README.md](deploy/README.md) for Cloud Run, Cloud Scheduler, and Docker build instructions.

## Architecture

- **Streamlit** — web UI (Day Planner + Todos sections)
- **SQLite** — local database (`data/day_planner.db`, gitignored)
- **Service layer** — shared by UI and both Telegram bots
- **python-telegram-bot** — polling bots with scheduled jobs
