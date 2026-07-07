from contextlib import contextmanager

from database.database import SessionLocal


@contextmanager
def get_db():
    from services.gcs_sync import gcs_sync_enabled
    from services.gcs_sync import persist_db_to_cloud_if_configured
    from services.gcs_sync import pull_db_from_gcs

    if gcs_sync_enabled():
        pull_db_from_gcs(dispose_connections=True)

    db = SessionLocal()

    try:
        yield db
        db.commit()

        if gcs_sync_enabled():
            persist_db_to_cloud_if_configured()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
