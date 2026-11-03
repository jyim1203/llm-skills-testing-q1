#!/usr/bin/env python
"""Extract attempt-level behavior/efficiency features from Harbor jobs.

Examples
--------
``python scripts/extract_behavior.py --jobs /path/to/jobs --out data/derived``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from skills_experiment.behavior import (  # noqa: E402
    extract,
    write_attempts_csv,
    write_events_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", required=True, help="Harbor job directory or parent of jobs")
    parser.add_argument(
        "--dataset",
        default="",
        help="Optional SWE-Bench Pro dataset JSON for fail-to-pass/pass-to-pass membership",
    )
    parser.add_argument("--out", default="data/derived", help="Output directory")
    args = parser.parse_args()

    root = Path(args.jobs)
    dataset = Path(args.dataset) if args.dataset else None
    attempts, events = extract(root, dataset)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_attempts_csv(out / "attempts.csv", attempts)
    write_events_csv(out / "events.csv", events)
    (out / "attempts.json").write_text(
        json.dumps(attempts, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"attempts={len(attempts)} events={len(events)} out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
