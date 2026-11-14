#!/usr/bin/env python3
"""Build the B/C-only plan for the frozen 20-task mechanism set.

The plan contains only the 10 new tasks, conditions B and C, two repeats each:
40 attempts. The 20 A attempts for those tasks already exist in the A-only
screens and are intentionally not rerun here. Combine A from the frozen task
file at analysis time.

Usage:
    python scripts/make_mechanism_20_bc_plan.py \
        --out data/mechanism-20bc-pilot-01 \
        --seed 20261116 \
        --job-prefix mechanism-20bc
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "data" / "mechanism-20-final" / "tasks.json"
DEFAULT_OUT = ROOT / "data" / "mechanism-20bc-pilot-01"
CONDITIONS = (
    ("B", "B_prompt_instructions"),
    ("C", "C_skill"),
)


def load_new_tasks(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload["tasks"]
    new_tasks = [task for task in tasks if task["source"] != "mechanism-pilot-01"]
    if len(tasks) != 20:
        raise SystemExit(f"expected 20 frozen tasks, found {len(tasks)}")
    if len(new_tasks) != 10:
        raise SystemExit(f"expected 10 new tasks, found {len(new_tasks)}")
    for task in new_tasks:
        if task.get("a_observed", {}).get("n") != 2:
            raise SystemExit(f"missing two A observations for {task['short']}")
        if not task.get("task_checksum") or not task.get("image_digest"):
            raise SystemExit(f"missing checksum or image digest for {task['short']}")
    return new_tasks


def build_plan(tasks: list[dict], seed: int, job_prefix: str) -> dict:
    order = []
    for task in tasks:
        for condition, condition_label in CONDITIONS:
            for repeat in (0, 1):
                order.append(
                    {
                        "task_id": task["task_id"],
                        "short": task["short"],
                        "stratum": task["stratum"],
                        "repo": task["repo"],
                        "condition": condition,
                        "condition_label": condition_label,
                        "repeat": repeat,
                    }
                )

    random.Random(seed).shuffle(order)
    for index, row in enumerate(order, start=1):
        row["order"] = index

    keys = {(row["task_id"], row["condition"], row["repeat"]) for row in order}
    if len(order) != 40 or len(keys) != 40:
        raise SystemExit("internal error: B/C plan must contain 40 unique attempts")

    return {
        "run_id": "mechanism-20bc-pilot-01",
        "purpose": "B/C-only extension for the 10 new tasks in the frozen 20-task mechanism set.",
        "benchmark": "SWE-bench Pro V2",
        "benchmark_commit": "66f92766bba642462d4bbe5479e83f91f9211862",
        "workflow_version": "v2",
        "frozen_tasks": "data/mechanism-20-final/tasks.json",
        "seed": seed,
        "job_prefix": job_prefix,
        "tasks": len(tasks),
        "conditions": [condition for condition, _ in CONDITIONS],
        "repeats": 2,
        "attempts": len(order),
        "a_reuse": {
            "included_in_plan": False,
            "source": "data/mechanism-20-final/tasks.json",
            "n_attempts": 20,
            "note": "A attempts for the 10 new tasks already exist and are combined at analysis time.",
        },
        "order": order,
    }


def build_tasks_file(tasks: list[dict]) -> dict:
    return {
        "run_id": "mechanism-20bc-pilot-01",
        "purpose": "Tasks in the B/C-only extension; A attempts are reused from the frozen set.",
        "benchmark": "SWE-bench Pro V2",
        "benchmark_commit": "66f92766bba642462d4bbe5479e83f91f9211862",
        "workflow_version": "v2",
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--job-prefix", default="mechanism-20bc")
    args = parser.parse_args()

    tasks = load_new_tasks(args.tasks)
    plan = build_plan(tasks, args.seed, args.job_prefix)
    task_file = build_tasks_file(tasks)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tasks.json").write_text(
        json.dumps(task_file, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "plan.json").write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8"
    )

    print(f"wrote {args.out / 'tasks.json'} ({len(tasks)} tasks)")
    print(f"wrote {args.out / 'plan.json'} ({len(plan['order'])} attempts)")
    print(f"seed={args.seed} job_prefix={args.job_prefix}")


if __name__ == "__main__":
    main()
