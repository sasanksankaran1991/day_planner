from contextlib import contextmanager

from database.database import SessionLocal


@contextmanager
def get_db():
    from services.gcs_sync import gcs_sync_enabled
    from services.gcs_sync import mark_db_modified
    from services.gcs_sync import persist_db_to_cloud_if_configured
    from services.gcs_sync import pull_db_from_gcs

    if gcs_sync_enabled():
        pull_db_from_gcs(dispose_connections=True)

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
                except Exception:
                    persist_db_to_cloud_if_configured(force=True)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
