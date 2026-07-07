from contextlib import contextmanager

from database.database import SessionLocal


@contextmanager
def get_db():
    db = SessionLocal()

    try:
        yield db
        db.commit()

        from services.gcs_sync import persist_db_to_cloud_if_configured

        persist_db_to_cloud_if_configured()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
