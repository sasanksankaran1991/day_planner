from pathlib import Path
import logging
import os

from dotenv import load_dotenv

from config.secret_manager import get_secret
from config.secret_manager import secret_manager_status

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# .env is optional — production uses Secret Manager only.
if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env", override=True)

APP_NAME = os.getenv("APP_NAME", "DayPlanner")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

DATABASE_NAME = os.getenv("DATABASE_NAME", "day_planner.db")

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")

DATA_DIR = BASE_DIR / DATA_FOLDER

DB_PATH = DATA_DIR / DATABASE_NAME

DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")

TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")

TELEGRAM_BOT_USERNAME = get_secret("TELEGRAM_BOT_USERNAME")

TODO_TELEGRAM_BOT_TOKEN = get_secret("TODO_TELEGRAM_BOT_TOKEN")

TODO_TELEGRAM_BOT_USERNAME = get_secret("TODO_TELEGRAM_BOT_USERNAME")

# Default admin is always created in the database (not loaded from Secret Manager).
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin").strip() or "admin"
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")

ADMIN_USERNAME = DEFAULT_ADMIN_USERNAME
ADMIN_PASSWORD = DEFAULT_ADMIN_PASSWORD

PORT = int(os.getenv("PORT", "8080"))

USE_CLOUD_SCHEDULER = os.getenv("USE_CLOUD_SCHEDULER", "false").lower() == "true"

SCHEDULER_SECRET = get_secret("SCHEDULER_SECRET")

SCHEDULER_POLL_SECONDS = int(os.getenv("SCHEDULER_POLL_SECONDS", "5"))

JOBS_SERVICE_URL = os.getenv("JOBS_SERVICE_URL", f"http://127.0.0.1:{PORT}")

logger.debug("Secret loading: %s", secret_manager_status())
