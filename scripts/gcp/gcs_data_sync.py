#!/usr/bin/env python3
"""Pull/push Day Planner data files to/from GCS."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import DATA_DIR  # noqa: E402
from config.settings import DB_PATH  # noqa: E402


def _data_files() -> list[tuple[Path, str]]:
    files = [
        (DB_PATH, DB_PATH.name),
        (DATA_DIR / "todo_bot_persistence.pkl", "todo_bot_persistence.pkl"),
        (DATA_DIR / "telegram_offset_planner.txt", "telegram_offset_planner.txt"),
        (DATA_DIR / "telegram_offset_todo.txt", "telegram_offset_todo.txt"),
    ]
    return files


def _bucket_name() -> str:
    bucket = os.environ.get("GCS_DATA_BUCKET", "").strip()

    if not bucket:
        raise SystemExit("GCS_DATA_BUCKET is not set")

    return bucket


def pull() -> int:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(_bucket_name())

    for local_path, blob_name in _data_files():
        blob = bucket.blob(blob_name)

        if not blob.exists():
            print(f"skip (missing in GCS): {blob_name}")
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))
        print(f"pulled gs://{_bucket_name()}/{blob_name} -> {local_path}")

    return 0


def push() -> int:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(_bucket_name())

    for local_path, blob_name in _data_files():
        if not local_path.is_file():
            print(f"skip (missing locally): {local_path}")
            continue

        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local_path))
        print(f"pushed {local_path} -> gs://{_bucket_name()}/{blob_name}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Day Planner data with GCS")
    parser.add_argument("action", choices=["pull", "push"])
    args = parser.parse_args()

    if args.action == "pull":
        return pull()

    return push()


if __name__ == "__main__":
    raise SystemExit(main())
