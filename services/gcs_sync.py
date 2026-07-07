import os
import sys


def gcs_bucket() -> str | None:
    bucket = os.environ.get("GCS_DATA_BUCKET", "").strip()
    return bucket or None


def push_db_to_gcs() -> None:
    if not gcs_bucket():
        return

    try:
        from scripts.gcp.gcs_data_sync import push

        push()
    except Exception as exc:
        print(f"GCS push failed: {exc}", file=sys.stderr)


def pull_db_from_gcs() -> None:
    if not gcs_bucket():
        return

    try:
        from scripts.gcp.gcs_data_sync import pull

        pull()
    except Exception as exc:
        print(f"GCS pull failed: {exc}", file=sys.stderr)


def persist_db_to_cloud_if_configured() -> None:
    push_db_to_gcs()
