from contextlib import contextmanager
import logging

from database.database import SessionLocal

logger = logging.getLogger(__name__)

_gcs_tx_depth = 0


@contextmanager
def get_db(*, raise_on_push_error: bool = False):
    """SQLAlchemy session.

    GCS mode (individual_ikr style): commit locally, then push on write.
    No pull-before-write, no writer lock, no generation checks.
    """
    from services.gcs_sync import GcsSyncError
    from services.gcs_sync import db_was_modified
    from services.gcs_sync import gcs_sync_enabled
    from services.gcs_sync import mark_db_modified
    from services.gcs_sync import persist_db_to_cloud_if_configured

    global _gcs_tx_depth

    is_outer = _gcs_tx_depth == 0
    _gcs_tx_depth += 1
    db = SessionLocal()

    try:
        yield db
        had_writes = bool(db.new or db.dirty or db.deleted)
        db.commit()

        if had_writes and gcs_sync_enabled():
            mark_db_modified()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        _gcs_tx_depth -= 1

    if is_outer and gcs_sync_enabled() and db_was_modified():
        try:
            persist_db_to_cloud_if_configured()
        except GcsSyncError:
            if raise_on_push_error:
                raise
            logger.warning(
                "GCS push failed after commit; local database was updated."
            )
