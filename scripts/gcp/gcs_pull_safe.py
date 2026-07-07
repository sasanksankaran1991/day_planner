#!/usr/bin/env python3
"""Pull day_planner.db from GCS after closing SQLite connections."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.gcs_sync import pull_db_from_gcs  # noqa: E402


def main() -> int:
    pull_db_from_gcs(dispose_connections=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
