"""Shared helpers for Cloud Run Job entrypoints."""

from __future__ import annotations

import json

from services.gcs_sync import db_was_modified
from services.gcs_sync import push_db_if_modified
from services.gcs_sync import reset_db_modified_flag


def print_result(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def finish_job(payload: dict) -> int:
    payload = {
        **payload,
        "db_modified": db_was_modified(),
    }
    push_db_if_modified()
    print_result(payload)
    return 0


def start_job() -> None:
    """Call at the start of every Cloud Run Job."""
    reset_db_modified_flag()
