#!/usr/bin/env python3
"""Run Day Planner locally on Mac or Windows (no bash required).

Usage:
  python run.py setup          # install deps + init database
  python run.py ui             # Streamlit web app
  python run.py bot            # Day Planner Telegram bot
  python run.py todo-bot       # Todos Telegram bot
  python run.py init-db        # migrate + create admin user only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.dev_common import print_platform_hint  # noqa: E402
from scripts.dev_common import project_root  # noqa: E402
from scripts.dev_common import python_executable  # noqa: E402
from scripts.dev_common import run_command  # noqa: E402
from scripts.dev_common import venv_python  # noqa: E402


def _pip_install() -> int:
    py = python_executable()
    req = project_root() / "requirements.txt"
    print(f"Installing dependencies from {req.name}...")
    return run_command([str(py), "-m", "pip", "install", "-r", str(req)])


def _init_db() -> int:
    py = python_executable()
    return run_command([str(py), str(project_root() / "scripts" / "setup_local_db.py")])


def cmd_setup(_: argparse.Namespace) -> int:
    print_platform_hint()
    print()

    if venv_python() is None:
        print("Tip: create a virtual environment first:")
        if sys.platform == "win32":
            print("  python -m venv .venv")
            print("  .venv\\Scripts\\activate")
        else:
            print("  python3 -m venv .venv")
            print("  source .venv/bin/activate")
        print()

    env_file = project_root() / ".env"
    if not env_file.is_file():
        example = project_root() / ".env.example"
        if example.is_file():
            example.read_text(encoding="utf-8")
            print(f"Copy {example.name} to .env and add your Telegram tokens.")
            print(f"  cp .env.example .env   (Mac/Linux)")
            print(f"  copy .env.example .env (Windows)")
        print()

    code = _pip_install()
    if code != 0:
        return code

    print()
    return _init_db()


def cmd_init_db(_: argparse.Namespace) -> int:
    return _init_db()


def cmd_ui(_: argparse.Namespace) -> int:
    py = python_executable()
    app = project_root() / "app.py"
    print("Starting Streamlit at http://localhost:8501")
    print("Login: admin / admin")
    return run_command(
        [
            str(py),
            "-m",
            "streamlit",
            "run",
            str(app),
            "--server.headless=true",
        ],
    )


def cmd_bot(_: argparse.Namespace) -> int:
    py = python_executable()
    script = project_root() / "scripts" / "run_bot.py"
    print("Starting Day Planner Telegram bot...")
    return run_command([str(py), str(script)])


def cmd_todo_bot(_: argparse.Namespace) -> int:
    py = python_executable()
    script = project_root() / "scripts" / "run_todo_bot.py"
    print("Starting Todos Telegram bot...")
    return run_command([str(py), str(script)])


def main() -> int:
    if sys.version_info < (3, 9):
        print(
            "Python 3.9+ is required. "
            f"You are running {sys.version.split()[0]}.",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(
        description="Day Planner — local dev runner (Mac / Windows / Linux)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Install requirements and initialize the database")
    sub.add_parser("init-db", help="Run migrations and ensure admin user exists")
    sub.add_parser("ui", help="Start the Streamlit web app")
    sub.add_parser("bot", help="Start the Day Planner Telegram bot")
    sub.add_parser("todo-bot", help="Start the Todos Telegram bot")

    args = parser.parse_args()
    handlers = {
        "setup": cmd_setup,
        "init-db": cmd_init_db,
        "ui": cmd_ui,
        "bot": cmd_bot,
        "todo-bot": cmd_todo_bot,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
