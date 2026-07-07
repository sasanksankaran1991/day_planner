#!/usr/bin/env python3
"""Poll todos Telegram bot (Cloud Scheduler every 2 min)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._job_common import run_telegram_poll_job  # noqa: E402
from todo_bot.app import build_application  # noqa: E402


def main() -> int:
    return run_telegram_poll_job(
        job_name="todo-telegram-poll",
        build_application=build_application,
        bot_name="todo",
    )


if __name__ == "__main__":
    raise SystemExit(main())
