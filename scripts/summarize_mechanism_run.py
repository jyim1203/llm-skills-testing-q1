"""Summarize a completed mechanism-pilot run.

The unit of analysis is the task, not the attempt: attempts are averaged within
task-condition first, then conditions are compared across tasks.  The script
writes a small, reviewable summary plus a per-attempt manifest; raw Harbor jobs
remain the source of truth.

Usage:
    python scripts/summarize_mechanism_run.py \
        --experiment mechanism-pilot-01 \
        --plan data/mechanism-pilot-01/plan.json \
        --attempts data/derived/mechanism-pilot-01/attempts.json \
        --status data/mechanism-pilot-01/run_status.jsonl \
        --out results/mechanism-pilot-01
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

SEED = 20261103
N_RESAMPLES = 5000
METRICS = [
    "resolved",
    "test_before_edit",
    "read_before_edit",
    "time_to_first_edit_seconds",
    "total_tokens",
    "verification_rate",
    "test_calls",
    "steps",
    "tool_calls",
    "f2p_fraction",
    "p2p_fraction",
    "budget_exhausted",
    "patch_lines_changed",
    "skill_loaded",
]
CONTRASTS = [("C", "B"), ("B", "A"), ("C", "A")]
STRATA = [
    "ceiling",
    "floor_known",
    "floor_expected",
    "floor",
    "new_easy",
    "new_medium",
    "new_hard",
    "new_all",
]


def mean(values: Iterable[float]) -> float | None:
    values = list(values)
    return sum(values) / len(values) if values else None


def rate(values: Iterable[bool]) -> float | None:
    values = list(values)
    return sum(1 for value in values if value) / len(values) if values else None


def task_mean(rows: list[dict[str, Any]], task_id: str, condition: str, metric: str) -> float | None:
    values = [
        float(row[metric])
        for row in rows
        if row["task_id"] == task_id
        and row["condition"] == condition
        and row.get(metric) is not None
    ]
    return mean(values)


def condition_stats(rows: list[dict[str, Any]], tasks: list[str], metric: str) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for condition in "ABC":
        values = [task_mean(rows, task, condition, metric) for task in tasks]
        values = [value for value in values if value is not None]
        stats[condition] = {
            "n_tasks": len(values),
            "mean": mean(values),
            "median": statistics.median(values) if values else None,
            "sd": statistics.stdev(values) if len(values) > 1 else 0.0 if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    return stats


def bootstrap_ci(diffs: list[float], n_resamples: int = N_RESAMPLES, seed: int = SEED) -> list[float]:
    if not diffs:
        return [None, None]
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_resamples):
        means.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return [means[int(0.025 * n_resamples)], means[min(n_resamples - 1, int(0.975 * n_resamples))]]


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided sign test over discordant pairs."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2**n)
    return min(1.0, 2 * tail)


def rank_biserial(diffs: list[float]) -> float:
    """Matched-pairs rank-biserial correlation of the differences."""
    diffs = [diff for diff in diffs if diff != 0]
    if not diffs:
        return 0.0
    ordered = sorted(range(len(diffs)), key=lambda index: abs(diffs[index]))
    ranks = [0.0] * len(diffs)
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and abs(diffs[ordered[end + 1]]) == abs(diffs[ordered[index]]):
            end += 1
        rank = (index + 1 + end + 1) / 2
        for position in range(index, end + 1):
            ranks[ordered[position]] = rank
        index = end + 1
    positive = sum(ranks[i] for i, diff in enumerate(diffs) if diff > 0)
    negative = sum(ranks[i] for i, diff in enumerate(diffs) if diff < 0)
    return (positive - negative) / (positive + negative) if positive + negative else 0.0


def paired_effects(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, dict[str, Any]]:
    effects: dict[str, dict[str, Any]] = {}
    for condition, reference in CONTRASTS:
        for metric in METRICS:
            diffs = []
            used_tasks = []
            for task in tasks:
                value = task_mean(rows, task, condition, metric)
                ref = task_mean(rows, task, reference, metric)
                if value is None or ref is None:
                    continue
                diffs.append(value - ref)
                used_tasks.append(task)
            if not diffs:
                continue
            wins = sum(1 for diff in diffs if diff > 0)
            losses = sum(1 for diff in diffs if diff < 0)
            effects[f"{condition}-{reference}|{metric}"] = {
                "contrast": f"{condition}-{reference}",
                "metric": metric,
                "mean_diff": mean(diffs),
                "median_diff": statistics.median(diffs),
                "sd_diff": statistics.stdev(diffs) if len(diffs) > 1 else 0.0,
                "ci95": bootstrap_ci(diffs),
                "wins": wins,
                "losses": losses,
                "ties": len(diffs) - wins - losses,
                "n_tasks": len(diffs),
                "sign_test_p": sign_test(wins, losses),
                "rank_biserial": rank_biserial(diffs),
                "tasks": used_tasks,
            }
    return effects


def task_checksums(rows: list[dict[str, Any]]) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for row in rows:
        result_path = Path(row["job_dir"]) / row["trial_name"] / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        checksum = result["task_checksum"]
        previous = checksums.setdefault(row["task_id"], checksum)
        if previous != checksum:
            raise RuntimeError(f"inconsistent task checksum for {row['task_id']}")
    return checksums


def image_digests(task_ids: set[str]) -> dict[str, str | None]:
    try:
        output = subprocess.check_output(
            ["docker", "images", "--digests", "--format", "{{.Repository}}|{{.Tag}}|{{.Digest}}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return {task_id: None for task_id in task_ids}
    digests = {}
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) == 3 and parts[0] == "ghcr.io/scaleapi/swe-bench_pro-v2":
            digests[parts[1]] = parts[2] or None
    return {task_id: digests.get(task_id) for task_id in task_ids}


def load_status(path: Path) -> dict[int, dict[str, Any]]:
    status: dict[int, dict[str, Any]] = {}
    if not path.exists():
        return status
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            status[int(item["order"])] = item
    return status


def build_manifest(
    plan: dict[str, Any],
    rows: list[dict[str, Any]],
    status: dict[int, dict[str, Any]],
    checksums: dict[str, str],
    digests: dict[str, str | None],
    meta: dict[str, Any],
) -> dict[str, Any]:
    by_key = {(row["task_id"], row["condition"], row["repeat"]): row for row in rows}
    attempts = []
    for entry in plan["order"]:
        row = by_key[(entry["task_id"], entry["condition"], entry["repeat"])]
        run = status.get(int(entry["order"]), {})
        attempts.append(
            {
                "order": entry["order"],
                "job": run.get("job", row["attempt_id"].split("/")[0]),
                "task_id": entry["task_id"],
                "short": entry["short"],
                "repo": entry["repo"],
                "stratum": entry["stratum"],
                "condition": entry["condition"],
                "repeat": entry["repeat"],
                "rc": run.get("returncode"),
                "seconds": run.get("seconds"),
                "trial_name": row["trial_name"],
                "job_id": row["job_id"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "resolved": row["resolved"],
                "reward": row["reward"],
                "stop_reason": row["stop_reason"],
                "budget_exhausted": row["budget_exhausted"],
                "total_tokens": row["total_tokens"],
                "exception": row["exception"],
                "task_checksum": checksums[entry["task_id"]],
                "image_digest": digests.get(entry["task_id"]),
                "verifier_environment_mode": row["verifier_environment_mode"],
                "workflow_sha256": row["workflow_sha256"],
                "system_prompt_sha256": row["system_prompt_sha256"],
                "task_prompt_sha256": row["task_prompt_sha256"],
            }
        )
    return {"schema_version": 1, "metadata": meta, "attempts": attempts}


def build_summary(
    rows: list[dict[str, Any]],
    plan: dict[str, Any],
    checksums: dict[str, str],
    digests: dict[str, str | None],
    meta: dict[str, Any],
) -> dict[str, Any]:
    tasks = sorted({row["task_id"] for row in rows})
    conditions = {condition: [row for row in rows if row["condition"] == condition] for condition in "ABC"}
    task_rows = {}
    for task in tasks:
        entry = next(entry for entry in plan["order"] if entry["task_id"] == task)
        task_rows[task] = {
            "short": entry["short"],
            "repo": entry["repo"],
            "stratum": entry["stratum"],
            "task_checksum": checksums[task],
            "image_digest": digests.get(task),
            "conditions": {},
        }
        for condition in "ABC":
            attempts = [row for row in rows if row["task_id"] == task and row["condition"] == condition]
            task_rows[task]["conditions"][condition] = {
                "n": len(attempts),
                "resolved": sum(1 for row in attempts if row["resolved"]),
                "budget_exhausted": sum(1 for row in attempts if row["budget_exhausted"]),
                "total_tokens_mean": mean(row["total_tokens"] for row in attempts),
                "test_before_edit_rate": rate(row["test_before_edit"] for row in attempts),
                "read_before_edit_rate": rate(row["read_before_edit"] for row in attempts),
                "verification_rate": rate(row["verification_rate"] for row in attempts),
                "test_calls_mean": mean(row["test_calls"] for row in attempts),
                "steps_mean": mean(row["steps"] for row in attempts),
                "f2p_passed": sum(row["f2p_passed"] for row in attempts),
                "f2p_total": sum(row["f2p_total"] for row in attempts),
                "p2p_passed": sum(row["p2p_passed"] for row in attempts),
                "p2p_total": sum(row["p2p_total"] for row in attempts),
                "patch_lines_changed_mean": mean(row["patch_lines_changed"] for row in attempts),
            }

    strata = {}
    for stratum in STRATA:
        if stratum == "new_all":
            selected = [task for task in tasks if task_rows[task]["stratum"].startswith("new_")]
        elif stratum == "floor":
            selected = [task for task in tasks if task_rows[task]["stratum"].startswith("floor_")]
        else:
            selected = [task for task in tasks if task_rows[task]["stratum"] == stratum]
        strata[stratum] = {"tasks": [task_rows[task]["short"] for task in selected], "n_tasks": len(selected), "conditions": {}}
        for condition in "ABC":
            attempts = [row for row in rows if row["task_id"] in selected and row["condition"] == condition]
            p2p_total = sum(row["p2p_total"] for row in attempts)
            p2p_passed = sum(row["p2p_passed"] for row in attempts)
            f2p_total = sum(row["f2p_total"] for row in attempts)
            f2p_passed = sum(row["f2p_passed"] for row in attempts)
            strata[stratum]["conditions"][condition] = {
                "n_attempts": len(attempts),
                "resolved_rate": rate(row["resolved"] for row in attempts),
                "total_tokens_mean": mean(row["total_tokens"] for row in attempts),
                "test_before_edit_rate": rate(row["test_before_edit"] for row in attempts),
                "verification_rate": rate(row["verification_rate"] for row in attempts),
                "test_calls_mean": mean(row["test_calls"] for row in attempts),
                "budget_exhausted_rate": rate(row["budget_exhausted"] for row in attempts),
                "f2p_fraction": f2p_passed / f2p_total if f2p_total else None,
                "p2p_fraction": p2p_passed / p2p_total if p2p_total else None,
            }

    return {
        "schema_version": 1,
        "metadata": meta,
        "quality": {
            "n_attempts": len(rows),
            "n_tasks": len(tasks),
            "exceptions": sum(1 for row in rows if row["exception"]),
            "budget_exhausted": sum(1 for row in rows if row["budget_exhausted"]),
            "by_condition": {
                condition: {
                    "n": len(conditions[condition]),
                    "resolved": sum(1 for row in conditions[condition] if row["resolved"]),
                    "budget_exhausted": sum(1 for row in conditions[condition] if row["budget_exhausted"]),
                    "skill_loaded": sum(1 for row in conditions[condition] if row["skill_loaded"]),
                    "exceptions": sum(1 for row in conditions[condition] if row["exception"]),
                }
                for condition in "ABC"
            },
        },
        "condition_stats": {metric: condition_stats(rows, tasks, metric) for metric in METRICS},
        "paired": paired_effects(rows, tasks),
        "task_table": task_rows,
        "strata": strata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default="mechanism-pilot-01")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--harness-commit-at-run", default="a13fe23")
    parser.add_argument("--harbor-version", default="0.25.0")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    rows = json.loads(args.attempts.read_text(encoding="utf-8"))
    status = load_status(args.status)
    checksums = task_checksums(rows)
    digests = image_digests({row["task_id"] for row in rows})

    # The provider-returned model ID is in the event stream; the extracted
    # attempt rows intentionally leave model_id null when Harbor metadata is
    # absent.
    api_model = None
    for row in rows:
        events_path = Path(row["job_dir"]) / row["trial_name"] / "agent" / "events.jsonl"
        if not events_path.exists():
            continue
        first = events_path.read_text(encoding="utf-8").splitlines()[0]
        event = json.loads(first)
        api_model = event.get("model_id")
        if api_model:
            break

    started = min(row["started_at"] for row in rows)
    finished = max(row["finished_at"] for row in rows)
    meta = {
        "run_id": args.experiment,
        "seed": plan["seed"],
        "workflow_version": "v2",
        "model_profile": "deepseek-flash-1017",
        "api_model_id": api_model or "deepseek-flash",
        "model_provider": "https://api.deepseek.com",
        "thinking": "enabled",
        "reasoning_effort": "medium",
        "response_cap_tokens": 16384,
        "cumulative_cap_tokens": 1000000,
        "step_cap": 80,
        "time_cap_seconds": 3000,
        "agent": "skills_experiment.harbor_agent:HarborSkillsAgent",
        "harbor_version": args.harbor_version,
        "harness_commit_at_run": args.harness_commit_at_run,
        "pro_repo_commit": "66f92766bba642462d4bbe5479e83f91f9211862",
        "verifier_environment_mode": sorted({row["verifier_environment_mode"] for row in rows}),
        "concurrency": 2,
        "started_at": started,
        "finished_at": finished,
        "n_attempts": len(rows),
        "n_tasks": len({row["task_id"] for row in rows}),
        "workflow_sha256": sorted({row["workflow_sha256"] for row in rows}),
    }
    manifest = build_manifest(plan, rows, status, checksums, digests, meta)
    summary = build_summary(rows, plan, checksums, digests, meta)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out / "analysis.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out / 'run_manifest.json'}")
    print(f"wrote {args.out / 'analysis.json'}")
    print(json.dumps(summary["quality"], indent=2))
    print(f"dates: {started} .. {finished}")


if __name__ == "__main__":
    main()
