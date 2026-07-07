from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from config.settings import DB_PATH

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@event.listens_for(Session, "before_flush")
def _track_session_writes(session, flush_context, instances) -> None:
    """Repositories flush() before commit; track writes here so GCS push runs."""
    if session.new or session.dirty or session.deleted:
        session.info["has_writes"] = True


def dispose_engine() -> None:
    """Close pooled SQLite connections before replacing the db file on disk."""
    engine.dispose()

