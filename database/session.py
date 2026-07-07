from contextlib import contextmanager
import logging

from database.database import SessionLocal

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    from services.gcs_sync import GcsSyncError
    from services.gcs_sync import gcs_sync_enabled
    from services.gcs_sync import mark_db_modified
    from services.gcs_sync import persist_db_to_cloud_if_configured

    # GCS pull happens once per container (entrypoint), Streamlit session
    # (app.py), or job start — not on every DB access.
    db = SessionLocal()
    had_writes = False

    try:
        yield db
        had_writes = bool(db.new or db.dirty or db.deleted)
        db.commit()

        if had_writes:
            mark_db_modified()
            if gcs_sync_enabled():
                try:
                    persist_db_to_cloud_if_configured(force=False)
                except GcsSyncError:
                    logger.warning(
                        "GCS push skipped: remote database changed first. "
                        "Refresh the page and retry your edit."
                    )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()