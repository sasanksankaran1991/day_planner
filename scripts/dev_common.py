from __future__ import annotations

"""Cross-platform helpers for local development (Mac, Windows, Linux)."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping
from typing import Sequence


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def venv_python() -> Path | None:
    root = project_root()
    if sys.platform == "win32":
        candidate = root / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = root / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def python_executable() -> Path:
    return venv_python() or Path(sys.executable)


def local_env() -> dict[str, str]:
    """Environment for local runs: .env file + no GCP sync unless explicitly set."""
    env = os.environ.copy()
    env.setdefault("USE_SECRET_MANAGER", "false")
    env.setdefault("USE_CLOUD_SCHEDULER", "false")

    if not env.get("GCS_DATA_BUCKET", "").strip():
        env["GCS_DATA_BUCKET"] = ""

    return env


def run_command(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    merged = local_env()
    if env:
        merged.update(env)

    completed = subprocess.run(
        list(args),
        cwd=str(cwd or project_root()),
        env=merged,
        check=False,
    )
    return int(completed.returncode)


def print_platform_hint() -> None:
    root = project_root()
    py = python_executable()
    venv = venv_python()
    print(f"Project: {root}")
    print(f"Python:  {py}")
    print(f"Venv:    {'yes' if venv else 'no (.venv not found — using system Python)'}")
    print(f"OS:      {sys.platform}")
