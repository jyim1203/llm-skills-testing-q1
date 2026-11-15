#!/usr/bin/env python3
"""Combine the original pilot, new A screens, and new B/C extension.

Produces a single 120-attempt plan/status/attempts table for the frozen 20-task
set. The combined plan uses the summarizer's existing stratum labels:
ceiling, floor_known, new_easy, new_medium, new_hard.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_TASKS = ROOT / "data" / "mechanism-20-final" / "tasks.json"
OUT = ROOT / "data" / "mechanism-20-combined"
DERIVED_OUT = ROOT / "data" / "derived" / "mechanism-20-combined"

SOURCES = [
    (
        "mechanism-pilot-01",
        ROOT / "data" / "derived" / "mechanism-pilot-01" / "attempts.json",
        ROOT / "data" / "mechanism-pilot-01" / "run_status.jsonl",
    ),
    (
        "mechanism-20a-pilot-01",
        ROOT / "data" / "derived" / "mechanism-20a-pilot-01" / "attempts.json",
        ROOT / "data" / "mechanism-20a-pilot-01" / "run_status.jsonl",
    ),
    (
        "mechanism-20a-screen-02",
        ROOT / "data" / "derived" / "mechanism-20a-screen-02" / "attempts.json",
        ROOT / "data" / "mechanism-20a-screen-02" / "run_status.jsonl",
    ),
    (
        "mechanism-20a-screen-03",
        ROOT / "data" / "derived" / "mechanism-20a-screen-03" / "attempts.json",
        ROOT / "data" / "mechanism-20a-screen-03" / "run_status.jsonl",
    ),
    (
        "mechanism-20bc-pilot-01",
        ROOT / "data" / "derived" / "mechanism-20bc-pilot-01" / "attempts.json",
        ROOT / "data" / "mechanism-20bc-pilot-01" / "run_status.jsonl",
    ),
]

ANALYSIS_STRATUM = {
    "ceiling": "ceiling",
    "floor": "floor",
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_job_dir(value: str) -> str:
    """Normalize Windows and WSL paths to a WSL path for the summarizer."""
    if value.startswith("C:/"):
        return "/mnt/c/" + value[3:]
    if value.startswith("C:\\"):
        return "/mnt/c/" + value[3:].replace("\\", "/")
    return value


def main() -> None:
    final = read_json(FINAL_TASKS)
    tasks = final["tasks"]
    final_by_id = {task["task_id"]: task for task in tasks}
    if len(tasks) != 20 or len(final_by_id) != 20:
        raise SystemExit("expected 20 unique frozen tasks")

    all_attempts = []
    status_by_job = {}
    for source_run, attempts_path, status_path in SOURCES:
        source_attempts = read_json(attempts_path)
        for attempt in source_attempts:
            if attempt["task_id"] in final_by_id:
                attempt = dict(attempt)
                attempt["job_dir"] = normalize_job_dir(attempt["job_dir"])
                attempt["source_run"] = source_run
                all_attempts.append(attempt)
        if status_path.exists():
            for line in status_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    status_by_job[item["job"]] = item

    by_key = {}
    for attempt in all_attempts:
        key = (attempt["task_id"], attempt["condition"], attempt["repeat"])
        if key in by_key:
            raise SystemExit(f"duplicate attempt key: {key}")
        by_key[key] = attempt

    if len(by_key) != 120:
        raise SystemExit(f"expected 120 attempts, found {len(by_key)}")

    plan_rows = []
    status_rows = []
    for task in tasks:
        for condition in ("A", "B", "C"):
            for repeat in (0, 1):
                key = (task["task_id"], condition, repeat)
                if key not in by_key:
                    raise SystemExit(f"missing attempt: {key}")
                attempt = by_key[key]
                order = len(plan_rows) + 1
                job = attempt["attempt_id"].split("/")[0]
                status = status_by_job.get(job)
                if status is None:
                    raise SystemExit(f"missing launcher status for {job}")
                plan_rows.append(
                    {
                        "task_id": task["task_id"],
                        "short": task["short"],
                        "stratum": ANALYSIS_STRATUM[task["stratum"]],
                        "final_stratum": task["stratum"],
                        "repo": task["repo"],
                        "condition": condition,
                        "condition_label": {
                            "A": "A_baseline",
                            "B": "B_prompt_instructions",
                            "C": "C_skill",
                        }[condition],
                        "repeat": repeat,
                        "order": order,
                        "source_run": attempt["source_run"],
                    }
                )
                status_rows.append(
                    {
                        "order": order,
                        "job": job,
                        "returncode": status["returncode"],
                        "seconds": status["seconds"],
                        "log": status.get("log"),
                        "source_run": attempt["source_run"],
                    }
                )

    plan = {
        "run_id": "mechanism-20-combined",
        "purpose": "Combined 20-task analysis: original 60 attempts + new A screens + new B/C extension.",
        "benchmark": final["benchmark"],
        "benchmark_commit": final["benchmark_commit"],
        "workflow_version": final["workflow_version"],
        "seed": "mixed: 20261103/20261113/20261114/20261115/20261116",
        "tasks": len(tasks),
        "conditions": ["A", "B", "C"],
        "repeats": 2,
        "attempts": len(plan_rows),
        "components": [
            {"run_id": source_run, "status_file": str(status_path.relative_to(ROOT))}
            for source_run, _, status_path in SOURCES
        ],
        "order": plan_rows,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    DERIVED_OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (OUT / "run_status.jsonl").write_text(
        "\n".join(json.dumps(row) for row in status_rows) + "\n", encoding="utf-8"
    )
    (DERIVED_OUT / "attempts.json").write_text(
        json.dumps(all_attempts, indent=2) + "\n", encoding="utf-8"
    )

    fieldnames = list(all_attempts[0].keys())
    for attempt in all_attempts[1:]:
        for key in attempt:
            if key not in fieldnames:
                fieldnames.append(key)
    with (DERIVED_OUT / "attempts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for attempt in all_attempts:
            row = {
                key: json.dumps(value) if isinstance(value, (dict, list)) else value
                for key, value in attempt.items()
            }
            writer.writerow(row)

    print(f"wrote {OUT / 'plan.json'} ({len(plan_rows)} attempts)")
    print(f"wrote {OUT / 'run_status.jsonl'} ({len(status_rows)} attempts)")
    print(f"wrote {DERIVED_OUT / 'attempts.json'} ({len(all_attempts)} attempts)")
    print(f"wrote {DERIVED_OUT / 'attempts.csv'} ({len(all_attempts)} attempts)")


if __name__ == "__main__":
    main()
