#!/usr/bin/env python
"""End-to-end dry run of the whole pipeline (mock model, noop sandbox).

    python scripts/smoke.py

Exercises all three conditions, isolation, logging, and patch capture without
touching the network or spending money.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["smoke", *sys.argv[1:]]))
