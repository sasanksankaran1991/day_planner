#!/usr/bin/env python3
"""Poll planner Telegram bot (Cloud Scheduler every 2 min)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bot.app import build_application  # noqa: E402
from database.init_db import initialize_database  # noqa: E402
from database.migrate import migrate_database  # noqa: E402
from scripts._job_common import finish_job  # noqa: E402
from services.gcs_sync import pull_db_from_gcs  # noqa: E402
from services.telegram_poll_runner import run_telegram_poll_sync  # noqa: E402
from services.user_service import UserService  # noqa: E402


def main() -> int:
    pull_db_from_gcs()
    migrate_database()
    initialize_database()
    UserService.ensure_admin_exists()

    result = run_telegram_poll_sync(
        build_application=build_application,
        bot_name="planner",
    )

    return finish_job({"job": "planner-telegram-poll", **result})


if __name__ == "__main__":
    raise SystemExit(main())
