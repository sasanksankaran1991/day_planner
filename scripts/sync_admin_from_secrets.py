#!/usr/bin/env python3
"""Sync admin user from Secret Manager into the database (run as Cloud Run Job)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import ADMIN_USERNAME  # noqa: E402
from database.init_db import initialize_database  # noqa: E402
from database.migrate import migrate_database  # noqa: E402
from scripts._job_common import finish_job  # noqa: E402
from scripts._job_common import start_job  # noqa: E402
from services.gcs_sync import pull_db_from_gcs  # noqa: E402
from services.user_service import UserService  # noqa: E402


def main() -> int:
    start_job()
    pull_db_from_gcs()
    migrate_database()
    initialize_database()
    UserService.ensure_admin_exists()

    return finish_job(
        {
            "job": "sync-admin",
            "admin_username": ADMIN_USERNAME,
            "message": "Admin synced from Secret Manager when needed.",
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
