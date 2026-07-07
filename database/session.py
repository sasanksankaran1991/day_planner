from contextlib import contextmanager
import logging

from database.database import SessionLocal

logger = logging.getLogger(__name__)


def _db_write_holder() -> str:
    import os

    job_name = os.environ.get("CLOUD_RUN_JOB")
    if job_name:
        execution = os.environ.get("CLOUD_RUN_EXECUTION") or "job"
        return f"job:{job_name}:{execution}:write"

    return "ui:streamlit"


@contextmanager
def get_db():
    from services.gcs_db_lock import gcs_db_writer_lock
    from services.gcs_sync import GcsSyncError
    from services.gcs_sync import gcs_sync_enabled
    from services.gcs_sync import mark_db_modified
    from services.gcs_sync import persist_db_to_cloud_if_configured
    from services.gcs_sync import pull_db_from_gcs

    db = SessionLocal()
    had_writes = False

    try:
        yield db
        had_writes = bool(db.new or db.dirty or db.deleted)

        if had_writes and gcs_sync_enabled():
            with gcs_db_writer_lock(holder=_db_write_holder()):
                pull_db_from_gcs(dispose_connections=True)
                db.commit()
                mark_db_modified()
                persist_db_to_cloud_if_configured(force=False)
        else:
            db.commit()

    except GcsSyncError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
