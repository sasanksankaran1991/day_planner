"""Shared helpers for Cloud Run Job entrypoints."""

from __future__ import annotations

import json
import sys

from services.gcs_sync import push_db_to_gcs


def print_result(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def finish_job(payload: dict) -> int:
    push_db_to_gcs()
    print_result(payload)
    return 0
