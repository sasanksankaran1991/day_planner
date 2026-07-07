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


def push_db_to_gcs(*, require_generation_match: bool = True) -> None:
    if not gcs_sync_enabled():
        return

    from database.database import dispose_engine

    dispose_engine()

    try:
        from scripts.gcp.gcs_data_sync import push

        exit_code = push(require_generation_match=require_generation_match)

        if exit_code != 0:
            raise GcsSyncError(
                "Database was not saved to cloud storage because a newer copy "
                "exists (likely a scheduler job wrote first). Please retry."
            )
    except GcsSyncError:
        raise
    except Exception as exc:
        logger.exception("GCS push failed")
        raise GcsSyncError(f"Could not push database to GCS: {exc}") from exc


def persist_db_to_cloud_if_configured(*, force: bool = False) -> None:
    push_db_to_gcs(require_generation_match=not force)


def push_db_if_modified(*, force: bool = False) -> None:
    if not db_was_modified():
        logger.info("GCS push skipped: no database writes in this run.")
        return

    try:
        persist_db_to_cloud_if_configured(force=force)
    except Exception:
        if not force:
            logger.warning("GCS push retry with force=True")
            persist_db_to_cloud_if_configured(force=True)
        else:
            raise

    reset_db_modified_flag()
