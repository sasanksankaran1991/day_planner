from contextlib import contextmanager
import logging

from database.database import SessionLocal

logger = logging.getLogger(__name__)

_gcs_tx_depth = 0


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
    from services.gcs_sync import db_was_modified
    from services.gcs_sync import gcs_sync_enabled
    from services.gcs_sync import mark_db_modified
    from services.gcs_sync import persist_db_to_cloud_if_configured
    from services.gcs_sync import pull_db_from_gcs

    global _gcs_tx_depth

    if not gcs_sync_enabled():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return

    is_outer = _gcs_tx_depth == 0

    with gcs_db_writer_lock(holder=_db_write_holder()):
        if is_outer:
            pull_db_from_gcs(dispose_connections=True)

        _gcs_tx_depth += 1
        db = SessionLocal()

        try:
            yield db
            had_writes = bool(db.new or db.dirty or db.deleted)
            db.commit()

            if had_writes:
                mark_db_modified()

        except GcsSyncError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            _gcs_tx_depth -= 1

        if is_outer and db_was_modified():
            persist_db_to_cloud_if_configured(force=False)
