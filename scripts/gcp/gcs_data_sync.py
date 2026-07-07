"""Pull/push Day Planner data files to/from GCS."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import DATA_DIR  # noqa: E402
from config.settings import DB_PATH  # noqa: E402

DB_GENERATION_FILE = DATA_DIR / ".gcs_db_generation"

TELEGRAM_OFFSET_BLOBS = (
    "telegram_offset_planner.txt",
    "telegram_offset_todo.txt",
)


def _data_files() -> list[tuple[Path, str]]:
    return [
        (DB_PATH, DB_PATH.name),
        (DATA_DIR / "todo_bot_persistence.pkl", "todo_bot_persistence.pkl"),
        (DATA_DIR / "telegram_offset_planner.txt", "telegram_offset_planner.txt"),
        (DATA_DIR / "telegram_offset_todo.txt", "telegram_offset_todo.txt"),
    ]


def _bucket_name() -> str:
    bucket = os.environ.get("GCS_DATA_BUCKET", "").strip()

    if not bucket:
        raise SystemExit("GCS_DATA_BUCKET is not set")

    return bucket


def _read_db_generation() -> int | None:
    if not DB_GENERATION_FILE.is_file():
        return None

    raw = DB_GENERATION_FILE.read_text(encoding="utf-8").strip()

    if raw.isdigit():
        return int(raw)

    return None


def _write_db_generation(generation: int) -> None:
    DB_GENERATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    DB_GENERATION_FILE.write_text(str(generation), encoding="utf-8")


def pull_files(blob_names: list[str]) -> int:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(_bucket_name())
    known = {name for _, name in _data_files()}

    for blob_name in blob_names:
        if blob_name not in known:
            print(f"skip (unknown blob): {blob_name}", file=sys.stderr)
            continue

        local_path = next(path for path, name in _data_files() if name == blob_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            print(f"skip (missing in GCS): {blob_name}")
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.reload()
        blob.download_to_filename(str(local_path))
        print(f"pulled gs://{_bucket_name()}/{blob_name} -> {local_path}")

        if blob_name == DB_PATH.name and blob.generation is not None:
            _write_db_generation(int(blob.generation))

    return 0


def pull() -> int:
    return pull_files([name for _, name in _data_files()])


def refresh_db_generation_from_gcs() -> None:
    """Update local generation tracker from GCS without replacing the db file."""
    from google.cloud import storage

    client = storage.Client()
    blob = client.bucket(_bucket_name()).blob(DB_PATH.name)

    if not blob.exists():
        return

    blob.reload()
    if blob.generation is not None:
        _write_db_generation(int(blob.generation))


def push(*, require_generation_match: bool = True) -> int:
    from google.api_core.exceptions import PreconditionFailed
    from google.cloud import storage

    if not DB_PATH.is_file():
        print(f"skip (missing locally): {DB_PATH}")
        return 0

    client = storage.Client()
    bucket = client.bucket(_bucket_name())
    db_blob = bucket.blob(DB_PATH.name)
    expected_generation = _read_db_generation()

    try:
        if require_generation_match and expected_generation is not None:
            db_blob.upload_from_filename(
                str(DB_PATH),
                if_generation_match=expected_generation,
            )
        else:
            db_blob.upload_from_filename(str(DB_PATH))
    except PreconditionFailed:
        print(
            "GCS push skipped: remote day_planner.db changed since last pull "
            "(another job wrote first). Local changes not uploaded.",
            file=sys.stderr,
        )
        return 1

    db_blob.reload()

    if db_blob.generation is not None:
        _write_db_generation(int(db_blob.generation))

    for local_path, blob_name in _data_files():
        if blob_name == DB_PATH.name:
            continue

        if not local_path.is_file():
            print(f"skip (missing locally): {local_path}")
            continue

        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local_path))
        print(f"pushed {local_path} -> gs://{_bucket_name()}/{blob_name}")

    print(f"pushed {DB_PATH} -> gs://{_bucket_name()}/{DB_PATH.name}")
    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync Day Planner data with GCS")
    parser.add_argument("action", choices=["pull", "push"])
    parser.add_argument(
        "--force",
        action="store_true",
        help="Push without generation check (use with care)",
    )
    args = parser.parse_args()

    if args.action == "pull":
        return pull()

    return push(require_generation_match=not args.force)


if __name__ == "__main__":
    raise SystemExit(main())
