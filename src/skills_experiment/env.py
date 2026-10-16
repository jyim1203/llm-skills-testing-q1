"""Minimal ``.env`` loader (no third-party dependency).

Loads ``KEY=VALUE`` lines from a ``.env`` file in the repository root into
``os.environ`` **without overriding** variables that are already set. This keeps
the framework dependency-free while still supporting the conventional
``.env`` workflow described in ``.env.example``.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import paths

_LOADED = False


def load_dotenv(path: Path | None = None, *, override: bool = False) -> bool:
    """Load a ``.env`` file. Returns True if a file was found and read."""
    global _LOADED
    env_path = Path(path) if path else paths.REPO_ROOT / ".env"
    if not env_path.exists():
        return False
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value
    _LOADED = True
    return True
