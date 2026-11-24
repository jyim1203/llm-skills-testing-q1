#!/usr/bin/env python3
"""Offline reproduction check for the mechanism-study artifacts.

Runs in about a second with no Docker, no network, and no API key. It checks the
parts of the study that *can* be verified from the branch alone:

* the committed prompt files still hash to the values recorded at run time;
* each plan is the frozen randomized design it claims to be;
* every attempt row agrees with its plan row and with the frozen task set
  (task ids, task checksums, image digests);
* the published per-condition statistics are reproducible from the manifest;
* the protocol anchors (Harbor, SWE-bench Pro commit, model caps) are intact.

Anything that depends on the model service or on Docker is out of scope here;
see ``docs/mechanism-study/REPLICATION.md`` for the full re-run.

Usage::

    python scripts/verify_replication.py
    python scripts/verify_replication.py --run mechanism-pilot-01
    python scripts/verify_replication.py --quiet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Protocol anchors. These are the values the reference runs were executed with;
# changing any of them makes the run a different study, not a replication.
PINNED = {
    "benchmark": "SWE-bench Pro V2",
    "pro_repo_commit": "66f92766bba642462d4bbe5479e83f91f9211862",
    "harbor_version": "0.25.0",
    "workflow_version": "v2",
    "workflow_sha256": "586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab",
    "model_profile": "deepseek-flash-1017",
    "api_model_id": "deepseek-flash",
    "model_provider": "https://api.deepseek.com",
    "agent": "skills_experiment.harbor_agent:HarborSkillsAgent",
    "response_cap_tokens": 16384,
    "cumulative_cap_tokens": 1000000,
    "step_cap": 80,
    "time_cap_seconds": 3000,
}

DEFAULT_RUNS = ["mechanism-pilot-01", "mechanism-20-combined"]
WORKFLOW_FILE = ROOT / "src" / "skills_experiment" / "assets" / "prompts" / "workflow_instructions_v2.md"
FROZEN_TASKS_FILE = ROOT / "data" / "mechanism-20-final" / "tasks.json"


def sha256_body(path: Path) -> str:
    """Hash a prompt file the way the harness does: UTF-8, stripped."""
    return hashlib.sha256(path.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Checks:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "", *, echo_detail: bool = True) -> bool:
        self.rows.append((name, bool(ok), detail))
        if not self.quiet:
            if ok:
                print(f"[ok  ] {name}" + (f" - {detail}" if detail and echo_detail else ""))
            else:
                print(f"[FAIL] {name}" + (f" - {detail}" if detail else ""))
        return bool(ok)

    def equal(self, name: str, actual: object, expected: object) -> bool:
        return self.check(
            name,
            actual == expected,
            detail=f"{actual!r} != {expected!r}",
            echo_detail=False,
        )

    @property
    def failures(self) -> list[tuple[str, bool, str]]:
        return [row for row in self.rows if not row[1]]


def verify_frozen_tasks(ck: Checks) -> dict:
    """Load the machine-readable frozen task set (ids, checksums, digests)."""
    if not ck.check("frozen task set present", FROZEN_TASKS_FILE.is_file(), str(FROZEN_TASKS_FILE.relative_to(ROOT))):
        return {}
    frozen = load_json(FROZEN_TASKS_FILE)
    tasks = frozen.get("tasks", [])
    ck.equal("frozen set benchmark commit", frozen.get("benchmark_commit"), PINNED["pro_repo_commit"])
    ck.equal("frozen set workflow version", frozen.get("workflow_version"), PINNED["workflow_version"])
    ck.equal("frozen set design", frozen.get("design", {}).get("attempts"), 120)
    ck.check(
        "frozen set has unique task ids",
        len({t["task_id"] for t in tasks}) == len(tasks) == 20,
        f"{len(tasks)} rows",
    )
    return {t["task_id"]: t for t in tasks}


def verify_prompts(ck: Checks) -> str:
    """The experimental text must still be byte-identical to what was run."""
    if not ck.check("workflow file present", WORKFLOW_FILE.is_file(), str(WORKFLOW_FILE.relative_to(ROOT))):
        return ""
    digest = sha256_body(WORKFLOW_FILE)
    ck.equal("workflow_instructions_v2.md body hash", digest, PINNED["workflow_sha256"])
    return digest


def verify_plan(run: str, ck: Checks) -> dict | None:
    plan_path = ROOT / "data" / run / "plan.json"
    if not ck.check(f"{run}: plan present", plan_path.is_file(), str(plan_path.relative_to(ROOT))):
        return None
    plan = load_json(plan_path)
    order = plan.get("order", [])
    attempts = plan.get("attempts")
    tasks = plan.get("tasks")
    repeats = plan.get("repeats")
    conditions = plan.get("conditions", [])

    ck.equal(f"{run}: plan run_id", plan.get("run_id"), run)
    ck.equal(f"{run}: plan workflow version", plan.get("workflow_version"), PINNED["workflow_version"])
    ck.check(f"{run}: plan attempt count", len(order) == attempts, f"{len(order)} rows vs {attempts} declared")
    ck.check(
        f"{run}: plan orders unique",
        len({row["order"] for row in order}) == len(order),
        f"{len(order)} rows",
    )
    ck.check(
        f"{run}: plan (task, condition, repeat) unique",
        len({(row["task_id"], row["condition"], row["repeat"]) for row in order}) == len(order),
        f"{len(order)} rows",
    )
    ck.equal(f"{run}: plan conditions", sorted({row["condition"] for row in order}), sorted(conditions))
    ck.check(
        f"{run}: plan task count",
        len({row["task_id"] for row in order}) == tasks,
        f"{len({row['task_id'] for row in order})} tasks vs {tasks} declared",
    )
    per_cell = Counter((row["task_id"], row["condition"]) for row in order)
    ck.check(
        f"{run}: plan repeats per task-condition",
        set(per_cell.values()) == {repeats},
        f"repeats observed {sorted(set(per_cell.values()))} vs {repeats} declared",
    )
    return plan


def verify_manifest(run: str, plan: dict, ck: Checks, workflow_digest: str, frozen: dict) -> list[dict]:
    manifest_path = ROOT / "results" / run / "run_manifest.json"
    if not ck.check(f"{run}: manifest present", manifest_path.is_file(), str(manifest_path.relative_to(ROOT))):
        return []
    manifest = load_json(manifest_path)
    meta = manifest.get("metadata", {})
    rows = manifest.get("attempts", [])

    # --- metadata anchors -------------------------------------------------
    for key in (
        "pro_repo_commit",
        "harbor_version",
        "workflow_version",
        "model_profile",
        "api_model_id",
        "model_provider",
        "agent",
        "response_cap_tokens",
        "cumulative_cap_tokens",
        "step_cap",
        "time_cap_seconds",
    ):
        ck.equal(f"{run}: metadata {key}", meta.get(key), PINNED[key])
    ck.equal(f"{run}: metadata run_id", meta.get("run_id"), run)
    ck.equal(f"{run}: metadata n_attempts", meta.get("n_attempts"), plan["attempts"])
    ck.equal(f"{run}: metadata n_tasks", meta.get("n_tasks"), plan["tasks"])

    # --- rows follow the plan ---------------------------------------------
    ck.equal(f"{run}: manifest schema version", manifest.get("schema_version"), 1)
    ck.check(
        f"{run}: manifest row count",
        len(rows) == plan["attempts"],
        f"{len(rows)} rows vs {plan['attempts']} planned",
    )
    by_order = {row["order"]: row for row in rows}
    ck.check(f"{run}: one row per plan order", set(by_order) == {row["order"] for row in plan["order"]})
    mismatched = []
    for plan_row in plan["order"]:
        row = by_order.get(plan_row["order"])
        if (
            row is None
            or row.get("task_id") != plan_row["task_id"]
            or row.get("condition") != plan_row["condition"]
            or row.get("repeat") != plan_row["repeat"]
        ):
            mismatched.append(plan_row["order"])
    ck.check(f"{run}: manifest rows match plan", not mismatched, f"{len(mismatched)} mismatched orders")

    # --- run quality ------------------------------------------------------
    ck.check(
        f"{run}: every attempt rc=0",
        set(row.get("rc") for row in rows) == {0},
        f"rc values {sorted({row.get('rc') for row in rows})}",
    )
    ck.check(f"{run}: no Harbor exception", not any(row.get("exception") for row in rows))

    # --- hashes from the run must match the tree --------------------------
    ck.equal(
        f"{run}: single workflow hash across attempts",
        {row.get("workflow_sha256") for row in rows},
        {workflow_digest},
    )
    per_condition_prompts = defaultdict(set)
    for row in rows:
        per_condition_prompts[row["condition"]].add(row.get("system_prompt_sha256"))
    ck.check(
        f"{run}: one system prompt per condition",
        all(len(values) == 1 for values in per_condition_prompts.values()),
        ", ".join(f"{cond}:{len(values)}" for cond, values in sorted(per_condition_prompts.items())),
    )

    # --- task identity versus the frozen set ------------------------------
    if frozen:
        unknown = {row["task_id"] for row in rows} - set(frozen)
        ck.check(f"{run}: attempts use frozen tasks", not unknown, f"{len(unknown)} unknown task ids")
        bad_checksum, bad_digest = [], []
        for row in rows:
            task = frozen.get(row["task_id"])
            if not task:
                continue
            if row.get("task_checksum") != task.get("task_checksum"):
                bad_checksum.append(row["order"])
            if row.get("image_digest") != task.get("image_digest"):
                bad_digest.append(row["order"])
        ck.check(f"{run}: task checksums match frozen set", not bad_checksum, f"{len(bad_checksum)} mismatched orders")
        ck.check(f"{run}: image digests match frozen set", not bad_digest, f"{len(bad_digest)} mismatched orders")

    ck.check(
        f"{run}: distinct tasks covered",
        len({row["task_id"] for row in rows}) == plan["tasks"],
        f"{len({row['task_id'] for row in rows})} tasks",
    )
    return rows


def verify_analysis(run: str, rows: list[dict], ck: Checks) -> dict | None:
    analysis_path = ROOT / "results" / run / "analysis.json"
    if not ck.check(f"{run}: analysis present", analysis_path.is_file(), str(analysis_path.relative_to(ROOT))):
        return None
    analysis = load_json(analysis_path)
    meta = analysis.get("metadata", {})
    quality = analysis.get("quality", {})

    ck.equal(f"{run}: analysis pro commit", meta.get("pro_repo_commit"), PINNED["pro_repo_commit"])
    ck.equal(f"{run}: analysis harbor version", meta.get("harbor_version"), PINNED["harbor_version"])
    ck.equal(f"{run}: analysis n_attempts", quality.get("n_attempts"), len(rows))
    ck.equal(f"{run}: analysis n_tasks", quality.get("n_tasks"), len({row["task_id"] for row in rows}))

    recomputed = defaultdict(lambda: {"n": 0, "resolved": 0, "budget_exhausted": 0, "exceptions": 0})
    for row in rows:
        cell = recomputed[row["condition"]]
        cell["n"] += 1
        cell["resolved"] += int(bool(row.get("resolved")))
        cell["budget_exhausted"] += int(bool(row.get("budget_exhausted")))
        cell["exceptions"] += int(bool(row.get("exception")))

    reported = quality.get("by_condition", {})
    ck.equal(f"{run}: analysis condition cells", sorted(reported), sorted(recomputed))
    for condition, cell in sorted(recomputed.items()):
        for key in ("n", "resolved", "budget_exhausted", "exceptions"):
            ck.equal(
                f"{run}: analysis {condition}.{key}",
                reported.get(condition, {}).get(key),
                cell[key],
            )

    ck.equal(
        f"{run}: analysis total exceptions",
        quality.get("exceptions"),
        sum(cell["exceptions"] for cell in recomputed.values()),
    )
    ck.equal(
        f"{run}: analysis total budget exhausted",
        quality.get("budget_exhausted"),
        sum(cell["budget_exhausted"] for cell in recomputed.values()),
    )

    # Manipulation check: only C ever loads the skill, and it always does.
    skill = {cond: reported.get(cond, {}).get("skill_loaded") for cond in ("A", "B", "C")}
    ok = (
        skill["C"] == recomputed["C"]["n"]
        and skill["A"] == 0
        and skill["B"] == 0
        and recomputed["A"]["n"] > 0
    )
    ck.check(
        f"{run}: skill manipulation check",
        ok,
        f"skill_loaded A={skill['A']} B={skill['B']} C={skill['C']} of C.n={recomputed['C']['n']}",
    )
    return quality


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="append", dest="runs", help="Run id to check (repeatable).")
    parser.add_argument("--quiet", action="store_true", help="Only print the summary.")
    args = parser.parse_args()
    runs = args.runs or DEFAULT_RUNS

    ck = Checks(quiet=args.quiet)
    workflow_digest = verify_prompts(ck)
    frozen = verify_frozen_tasks(ck)

    per_run_tasks: dict[str, set[str]] = {}
    for run in runs:
        plan = verify_plan(run, ck)
        if plan is None:
            continue
        rows = verify_manifest(run, plan, ck, workflow_digest, frozen)
        verify_analysis(run, rows, ck)
        per_run_tasks[run] = {row["task_id"] for row in rows}

    if len(per_run_tasks) > 1:
        smallest = min(per_run_tasks.values(), key=len)
        largest = max(per_run_tasks.values(), key=len)
        ck.check(
            "smaller run's tasks are a subset of the larger run's",
            smallest <= largest,
            f"{len(smallest)} vs {len(largest)} tasks",
        )

    total = len(ck.rows)
    failed = len(ck.failures)
    print()
    if failed:
        print(f"FAILED {failed}/{total} checks")
        for name, _, detail in ck.failures:
            print(f"  - {name}" + (f" — {detail}" if detail else ""))
        return 1
    print(f"PASSED {total}/{total} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
