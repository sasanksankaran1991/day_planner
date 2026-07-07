#!/usr/bin/env python3
"""Run all Telegram notification jobs (Cloud Scheduler every 1 min)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from database.init_db import initialize_database  # noqa: E402
from database.migrate import migrate_database  # noqa: E402
from jobs.planner import execute_block_starts_sync  # noqa: E402
from jobs.planner import execute_day_summaries_sync  # noqa: E402
from jobs.todo import execute_morning_notifications_sync  # noqa: E402
from jobs.todo import execute_task_end_notifications_sync  # noqa: E402
from jobs.todo import execute_task_reminders_sync  # noqa: E402
from scripts._job_common import finish_job  # noqa: E402
from scripts._job_common import job_db_session  # noqa: E402


def main() -> int:
    with job_db_session("notifications-tick"):
        migrate_database()
        initialize_database()

        results = [
            execute_block_starts_sync(),
            execute_day_summaries_sync(),
            execute_morning_notifications_sync(),
            execute_task_reminders_sync(),
            execute_task_end_notifications_sync(),
        ]

        return finish_job({"job": "notifications-tick", "results": results})


if __name__ == "__main__":
    raise SystemExit(main())
