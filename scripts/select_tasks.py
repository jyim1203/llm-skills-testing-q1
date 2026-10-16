#!/usr/bin/env python
"""Write (and optionally cache) the frozen SWE-bench Lite task selection.

    python scripts/select_tasks.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["select-tasks", *sys.argv[1:]]))
