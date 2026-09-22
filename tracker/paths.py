from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """Folder that contains the launched program (exe or repo root)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return app_dir() / "config.json"


def crash_log_path() -> Path:
    return app_dir() / "crash.log"
