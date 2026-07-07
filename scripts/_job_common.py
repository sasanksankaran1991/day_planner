"""Shared helpers for Cloud Run Job entrypoints."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Callable
from typing import Iterator

from database.init_db import initialize_database
from database.migrate import migrate_database
from services.gcs_db_lock import gcs_db_writer_lock
from services.gcs_sync import db_was_modified
from services.gcs_sync import gcs_sync_enabled
from services.gcs_sync import mark_db_modified
from services.gcs_sync import pull_db_from_gcs
from services.gcs_sync import pull_telegram_offsets_from_gcs
from services.gcs_sync import push_db_if_modified
from services.gcs_sync import reset_db_modified_flag
from services.telegram_poll_runner import fetch_telegram_updates_sync
from services.telegram_poll_runner import process_telegram_batch_sync
from telegram.ext import Application


def print_result(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def _job_holder(job_name: str) -> str:
    execution = (
        os.environ.get("CLOUD_RUN_EXECUTION")
        or os.environ.get("CLOUD_RUN_JOB")
        or "job"
    )
    return f"job:{job_name}:{execution}"


@contextmanager
def job_db_session(job_name: str) -> Iterator[None]:
    """Pull/push under the writer lock; job body runs unlocked so UI can interleave."""
    reset_db_modified_flag()

    if not gcs_sync_enabled():
        yield
        return

    holder = _job_holder(job_name)

    with gcs_db_writer_lock(holder=holder):
        pull_db_from_gcs()

    try:
        yield
    finally:
        with gcs_db_writer_lock(holder=holder):
            push_db_if_modified()


def run_telegram_poll_job(
    *,
    job_name: str,
    build_application: Callable[[], Application],
    bot_name: str,
) -> int:
    """Poll Telegram first; load full DB from GCS only when there are updates."""
    reset_db_modified_flag()

    if gcs_sync_enabled():
        pull_telegram_offsets_from_gcs()

    batch = fetch_telegram_updates_sync(
        build_application=build_application,
        bot_name=bot_name,
    )

    if batch is None:
        return finish_job(
            {
                "job": job_name,
                "bot": bot_name,
                "processed": 0,
                "db_loaded": False,
            }
        )

    holder = _job_holder(job_name)

    with gcs_db_writer_lock(holder=holder):
        pull_db_from_gcs()

    migrate_database()
    initialize_database()

    result = process_telegram_batch_sync(batch)
    mark_db_modified()

    with gcs_db_writer_lock(holder=holder):
        push_db_if_modified()

    return finish_job(
        {
            "job": job_name,
            "db_loaded": True,
            **result,
        }
    )


def finish_job(payload: dict) -> int:
    payload = {
        **payload,
        "db_modified": db_was_modified(),
    }
    print_result(payload)
    return 0
