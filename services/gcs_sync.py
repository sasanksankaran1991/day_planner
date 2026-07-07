import logging
import os

logger = logging.getLogger(__name__)


class GcsSyncError(RuntimeError):
    pass


def gcs_bucket() -> str | None:
    bucket = os.environ.get("GCS_DATA_BUCKET", "").strip()
    return bucket or None


def gcs_sync_enabled() -> bool:
    return bool(gcs_bucket())


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


def persist_db_to_cloud_if_configured() -> None:
    push_db_to_gcs(require_generation_match=True)
