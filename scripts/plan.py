#!/usr/bin/env python
"""Print the run matrix and fairness hashes without running anything.

    python scripts/plan.py --experiment pilot
    python scripts/plan.py --experiment pilot --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["plan", *sys.argv[1:]]))
