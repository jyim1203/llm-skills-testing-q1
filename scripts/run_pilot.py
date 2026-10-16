#!/usr/bin/env python
"""Run the pilot experiment.

    python scripts/run_pilot.py --dry-run
    python scripts/run_pilot.py --model claude-opus
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["run", "--experiment", "pilot", *sys.argv[1:]]))
