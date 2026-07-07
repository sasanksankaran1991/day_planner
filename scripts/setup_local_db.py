#!/usr/bin/env python3
"""Initialize local SQLite database (Mac / Windows — no GCS)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import DB_PATH  # noqa: E402
from config.settings import DEFAULT_ADMIN_PASSWORD  # noqa: E402
from config.settings import DEFAULT_ADMIN_USERNAME  # noqa: E402
from database.init_db import initialize_database  # noqa: E402
from database.migrate import migrate_database  # noqa: E402
from services.user_service import UserService  # noqa: E402


def main() -> int:
    migrate_database()
    initialize_database()
    UserService.ensure_admin_exists(reset_password=True)

    print(f"Database ready: {DB_PATH}")
    print(f"Login: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
