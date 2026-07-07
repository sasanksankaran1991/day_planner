import logging
import os

logger = logging.getLogger(__name__)

_db_modified = False


class GcsSyncError(RuntimeError):
    pass


def gcs_bucket() -> str | None:
    bucket = os.environ.get("GCS_DATA_BUCKET", "").strip()
    return bucket or None


def gcs_sync_enabled() -> bool:
    return bool(gcs_bucket())


def reset_db_modified_flag() -> None:
    global _db_modified
    _db_modified = False


def mark_db_modified() -> None:
    global _db_modified
    _db_modified = True


def db_was_modified() -> bool:
    return _db_modified


def pull_db_from_gcs(*, dispose_connections: bool = False) -> None:
    if not gcs_sync_enabled():
        return

    if dispose_connections:
        from database.database import dispose_engine

        dispose_engine()

    try:
        from scripts.gcp.gcs_data_sync import pull

        pull()
    except Exception as exc:
        logger.exception("GCS pull failed")
        raise GcsSyncError(f"Could not pull database from GCS: {exc}") from exc


def pull_telegram_offsets_from_gcs() -> None:
    """Pull only Telegram offset files (~few bytes) before polling."""
    if not gcs_sync_enabled():
        return

    try:
        from scripts.gcp.gcs_data_sync import TELEGRAM_OFFSET_BLOBS
        from scripts.gcp.gcs_data_sync import pull_files

        pull_files(list(TELEGRAM_OFFSET_BLOBS))
    except Exception as exc:
        logger.exception("GCS offset pull failed")
        raise GcsSyncError(f"Could not pull Telegram offsets from GCS: {exc}") from exc


def push_db_to_gcs() -> None:
    if not gcs_sync_enabled():
        return

    from database.database import dispose_engine

    dispose_engine()

    try:
        from scripts.gcp.gcs_data_sync import push

        push()
    except Exception as exc:
        logger.exception("GCS push failed")
        raise GcsSyncError(f"Could not push database to GCS: {exc}") from exc


def persist_db_to_cloud_if_configured() -> None:
    push_db_to_gcs()
    reset_db_modified_flag()


def push_db_if_modified() -> None:
    if not db_was_modified():
        logger.info("GCS push skipped: no database writes in this run.")
        return

    try:
        persist_db_to_cloud_if_configured()
    except GcsSyncError:
        logger.warning("GCS push failed at job end.")
    except Exception:
        logger.exception("GCS push failed at job end")
