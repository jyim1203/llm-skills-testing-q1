"""Filesystem locations used across the project.

The project is designed to be used from a source checkout (``pip install -e .``)
so that configs, data, and generated outputs live next to the code. Every path
can be overridden with the ``SKILLS_EXPERIMENT_ROOT`` environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path


def _detect_repo_root() -> Path:
    override = os.environ.get("SKILLS_EXPERIMENT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    # this file: <root>/src/skills_experiment/paths.py  ->  parents[2] == <root>
    return Path(__file__).resolve().parents[2]


REPO_ROOT: Path = _detect_repo_root()

SRC_DIR: Path = REPO_ROOT / "src"
PACKAGE_DIR: Path = SRC_DIR / "skills_experiment"

CONFIGS_DIR: Path = REPO_ROOT / "configs"
MODELS_DIR: Path = CONFIGS_DIR / "models"
CONDITIONS_DIR: Path = CONFIGS_DIR / "conditions"
EXPERIMENTS_DIR: Path = CONFIGS_DIR / "experiments"

DATA_DIR: Path = REPO_ROOT / "data"
INSTANCES_DIR: Path = DATA_DIR / "instances"
RUNS_DIR: Path = REPO_ROOT / "runs"

ASSETS_DIR: Path = PACKAGE_DIR / "assets"
PROMPTS_DIR: Path = ASSETS_DIR / "prompts"
SKILLS_DIR: Path = ASSETS_DIR / "skills"


def ensure_dirs() -> None:
    """Create the mutable output directories if they do not exist yet."""
    for path in (DATA_DIR, INSTANCES_DIR, RUNS_DIR):
        path.mkdir(parents=True, exist_ok=True)
