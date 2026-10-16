#!/usr/bin/env python
"""Regenerate the skill file from the workflow source of truth.

    python scripts/build_skill.py

Keeps Condition C's skill body byte-identical to Condition B's prompt text.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["build-skill", *sys.argv[1:]]))
