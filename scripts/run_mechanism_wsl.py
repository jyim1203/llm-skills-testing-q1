#!/usr/bin/env python3
"""Run the randomized mechanism plan through Harbor, two workers at a time.

Run this inside WSL as root (the Harbor install is root-owned):

    python3 scripts/run_mechanism_wsl.py \
      --plan data/mechanism-pilot-01/plan.json \
      --pro-dir "/mnt/c/Users/Jonat/UCSD/2026-2027/DSC 180A/SWE-bench_Pro-os"

Each plan row is one Harbor job with one trial.  The plan is already shuffled,
so launching in plan order keeps conditions interleaved.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR = Path("/root/.local/bin/harbor")
AGENT = "skills_experiment.harbor_agent:HarborSkillsAgent"


def job_name(row: dict) -> str:
    return (
        f"mechanism-v2-{int(row['order']):02d}-"
        f"{row['short']}-{row['condition']}-r{int(row['repeat'])}"
    )


def command(row: dict, pro_dir: Path) -> list[str]:
    return [
        str(HARBOR),
        "run",
        "-p",
        "v2/tasks",
        "-i",
        row["task_id"],
        "--agent",
        AGENT,
        "--ak",
        f"condition={row['condition']}",
        "--ak",
        "workflow_version=v2",
        "--ak",
        f"task_id={row['task_id']}",
        "--ak",
        f"repeat={int(row['repeat'])}",
        "-n",
        "1",
        "-y",
        "--job-name",
        job_name(row),
    ]


def run_one(row: dict, pro_dir: Path, pythonpath: str, log_dir: Path) -> dict:
    name = job_name(row)
    log_path = log_dir / f"{name}.log"
    started = time.time()
    env = dict(os.environ)
    env["PYTHONPATH"] = pythonpath
    try:
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.run(
                command(row, pro_dir),
                cwd=str(pro_dir),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3900,
            )
        return {
            "order": row["order"],
            "job": name,
            "returncode": proc.returncode,
            "seconds": round(time.time() - started, 1),
            "log": str(log_path),
        }
    except subprocess.TimeoutExpired:
        return {
            "order": row["order"],
            "job": name,
            "returncode": 124,
            "seconds": round(time.time() - started, 1),
            "log": str(log_path),
            "error": "timeout",
        }
    except Exception as exc:  # noqa: BLE001 - record and continue
        return {
            "order": row["order"],
            "job": name,
            "returncode": 1,
            "seconds": round(time.time() - started, 1),
            "log": str(log_path),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=str(ROOT / "data" / "mechanism-pilot-01" / "plan.json"))
    parser.add_argument("--pro-dir", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start", type=int, default=1, help="First plan order to run")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    rows = [r for r in plan["order"] if int(r["order"]) >= args.start]
    if args.limit:
        rows = rows[: args.limit]
    pro_dir = Path(args.pro_dir)
    pythonpath = str(ROOT / "src")
    log_dir = Path(args.plan).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    status_path = Path(args.plan).parent / "run_status.jsonl"

    if args.dry_run:
        for row in rows:
            print(" ".join(command(row, pro_dir)))
        return 0

    print(f"running {len(rows)} attempts with {args.workers} workers", flush=True)
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_one, row, pro_dir, pythonpath, log_dir): row
            for row in rows
        }
        for future in as_completed(futures):
            result = future.result()
            with status_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(result) + "\n")
            print(
                f"[{result['order']:02d}] rc={result['returncode']} "
                f"{result['seconds']}s {result['job']}",
                flush=True,
            )
    print(f"finished in {round(time.time() - started, 1)}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
