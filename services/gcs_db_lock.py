"""GCS-backed writer lock — one DB pull/write/push at a time across jobs and UI."""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Iterator

from services.gcs_sync import gcs_bucket

logger = logging.getLogger(__name__)

LOCK_BLOB_NAME = ".dp_db_writer_lock"
UI_PRIORITY_BLOB_NAME = ".dp_db_ui_priority"

_lock_depth = 0
_lock_generation: int | None = None


class GcsDbLockTimeout(TimeoutError):
    """Raised when a job or UI write could not acquire the DB writer lock in time."""


def _wait_timeout_sec() -> float:
    raw = os.environ.get("GCS_DB_LOCK_WAIT_SEC", "600").strip()
    return max(1.0, float(raw))


def _poll_interval_sec() -> float:
    raw = os.environ.get("GCS_DB_LOCK_POLL_SEC", "3").strip()
    return max(0.5, float(raw))


def _ui_poll_interval_sec() -> float:
    raw = os.environ.get("GCS_DB_LOCK_UI_POLL_SEC", "0.5").strip()
    return max(0.2, float(raw))


def _ui_priority_ttl_sec() -> float:
    raw = os.environ.get("GCS_UI_PRIORITY_TTL_SEC", "30").strip()
    return max(5.0, float(raw))


def _lock_ttl_sec() -> float:
    raw = os.environ.get("GCS_DB_LOCK_TTL_SEC", "900").strip()
    return max(60.0, float(raw))


def _bucket_blob(blob_name: str):
    from google.cloud import storage

    bucket_name = gcs_bucket()
    if not bucket_name:
        raise RuntimeError("GCS_DATA_BUCKET is not set")

    client = storage.Client()
    return client.bucket(bucket_name).blob(blob_name)


def _lock_blob():
    return _bucket_blob(LOCK_BLOB_NAME)


def _priority_blob():
    return _bucket_blob(UI_PRIORITY_BLOB_NAME)


def _is_ui_holder(holder: str) -> bool:
    return holder.startswith("ui:")


def _is_job_holder(holder: str) -> bool:
    return holder.startswith("job:")


def signal_ui_write_priority() -> None:
    """Tell waiting jobs to defer — a UI save is queued."""
    blob = _priority_blob()
    blob.upload_from_string(
        json.dumps({"requested_at": time.time()}),
        content_type="application/json",
    )
    logger.info("UI write priority signaled")


def clear_ui_write_priority() -> None:
    blob = _priority_blob()
    try:
        if blob.exists():
            blob.delete()
    except Exception:
        logger.exception("Failed to clear UI write priority flag")


def ui_write_priority_active() -> bool:
    blob = _priority_blob()
    if not blob.exists():
        return False

    blob.reload()
    try:
        data = json.loads(blob.download_as_text(encoding="utf-8"))
        requested_at = float(data.get("requested_at", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return False

    return (time.time() - requested_at) < _ui_priority_ttl_sec()


def _lock_payload(holder: str) -> str:
    now = time.time()
    return json.dumps(
        {
            "holder": holder,
            "acquired_at": now,
            "expires_at": now + _lock_ttl_sec(),
        }
    )


def _try_acquire_once(*, holder: str) -> int | None:
    from google.api_core.exceptions import PreconditionFailed

    if _is_job_holder(holder) and ui_write_priority_active():
        logger.info("Deferring job lock — UI write has priority")
        return None

    blob = _lock_blob()

    if blob.exists():
        blob.reload()
        try:
            data = json.loads(blob.download_as_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError, ValueError):
            data = {}

        if time.time() < float(data.get("expires_at", 0)):
            logger.info(
                "DB writer lock held by %s; waiting...",
                data.get("holder", "unknown"),
            )
            return None

        try:
            blob.delete(if_generation_match=blob.generation)
        except PreconditionFailed:
            return None

    try:
        blob.upload_from_string(
            _lock_payload(holder),
            content_type="application/json",
            if_generation_match=0,
        )
    except PreconditionFailed:
        return None

    blob.reload()
    if blob.generation is None:
        return None

    logger.info("DB writer lock acquired by %s (generation=%s)", holder, blob.generation)
    return int(blob.generation)


def _wait_and_acquire(*, holder: str) -> int:
    is_ui = _is_ui_holder(holder)
    deadline = time.time() + _wait_timeout_sec()
    poll = _ui_poll_interval_sec() if is_ui else _poll_interval_sec()

    while time.time() < deadline:
        generation = _try_acquire_once(holder=holder)
        if generation is not None:
            return generation

        time.sleep(poll)

    raise GcsDbLockTimeout(
        f"Timed out after {_wait_timeout_sec():.0f}s waiting for DB writer lock "
        f"(holder={holder}). Another writer is still running."
    )


def _release(*, generation: int) -> None:
    from google.api_core.exceptions import PreconditionFailed

    blob = _lock_blob()

    try:
        blob.delete(if_generation_match=generation)
        logger.info("DB writer lock released (generation=%s)", generation)
    except PreconditionFailed:
        logger.warning(
            "DB writer lock generation=%s was already released or stolen",
            generation,
        )


@contextmanager
def gcs_db_writer_lock(*, holder: str) -> Iterator[None]:
    """Acquire the global DB writer lock; UI holders get priority over jobs."""
    global _lock_depth, _lock_generation

    if not gcs_bucket():
        yield
        return

    if _lock_depth > 0:
        _lock_depth += 1
        try:
            yield
        finally:
            _lock_depth -= 1
        return

    is_ui = _is_ui_holder(holder)
    if is_ui:
        signal_ui_write_priority()

    generation = _wait_and_acquire(holder=holder)
    _lock_generation = generation
    _lock_depth = 1

    try:
        yield
    finally:
        _lock_depth = 0
        _lock_generation = None
        _release(generation=generation)
        if is_ui:
            clear_ui_write_priority()


def lock_is_held() -> bool:
    return _lock_depth > 0
