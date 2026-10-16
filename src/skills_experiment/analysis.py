"""Analysis of a finished (or partial) experiment.

Reads the run log and reports, per condition:

* the number of attempts and distinct tasks;
* the resolved rate over *counted* attempts (``resolved`` / ``unresolved``);
  infrastructure errors are reported separately and excluded from the
  denominator, per the failure-handling policy;
* mean tokens, tool calls, steps, and elapsed time.

Pairwise condition effects are computed at the **task level** (the unit of
randomization), with a task-level bootstrap confidence interval. The bootstrap
resamples *tasks* with replacement, so within-task attempts stay together; this
is the appropriate unit because tasks, not attempts, are independent.

Everything uses the standard library only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from . import paths
from .evaluation import policy
from .runlog import RunLogger, RunRecord


@dataclass
class ConditionStats:
    condition: str
    attempts: int = 0
    tasks: int = 0
    resolved: int = 0
    unresolved: int = 0
    infrastructure_errors: int = 0
    not_evaluated: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_call_count: int = 0
    steps: int = 0
    elapsed_seconds: float = 0.0
    tests_passed: int = 0
    tests_total: int = 0
    graded: int = 0

    @property
    def counted(self) -> int:
        return self.resolved + self.unresolved

    @property
    def resolved_rate(self) -> float:
        return self.resolved / self.counted if self.counted else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "attempts": self.attempts,
            "tasks": self.tasks,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "infrastructure_errors": self.infrastructure_errors,
            "not_evaluated": self.not_evaluated,
            "counted": self.counted,
            "resolved_rate": round(self.resolved_rate, 4),
            "mean_total_tokens": round((self.input_tokens + self.output_tokens) / self.attempts, 1)
            if self.attempts
            else 0.0,
            "mean_tool_calls": round(self.tool_call_count / self.attempts, 2) if self.attempts else 0.0,
            "mean_steps": round(self.steps / self.attempts, 2) if self.attempts else 0.0,
            "mean_elapsed_seconds": round(self.elapsed_seconds / self.attempts, 2)
            if self.attempts
            else 0.0,
            "graded_attempts": self.graded,
            "total_tests_passed": self.tests_passed,
            "total_tests_total": self.tests_total,
            "mean_tests_passed": round(self.tests_passed / self.graded, 1) if self.graded else 0.0,
        }


@dataclass
class Effect:
    contrast: str  # e.g. "C_skill - A_baseline"
    condition: str
    reference: str
    diff: float
    ci_low: float
    ci_high: float
    n_tasks: int
    n_resamples: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "contrast": self.contrast,
            "diff": round(self.diff, 4),
            "ci95": [round(self.ci_low, 4), round(self.ci_high, 4)],
            "n_tasks": self.n_tasks,
            "n_resamples": self.n_resamples,
        }


def condition_stats(records: Iterable[RunRecord]) -> dict[str, ConditionStats]:
    stats: dict[str, ConditionStats] = {}
    seen_tasks: dict[str, set[str]] = {}
    for rec in records:
        st = stats.setdefault(rec.condition, ConditionStats(condition=rec.condition))
        st.attempts += 1
        seen_tasks.setdefault(rec.condition, set()).add(rec.instance_id)
        st.input_tokens += rec.input_tokens
        st.output_tokens += rec.output_tokens
        st.tool_call_count += rec.tool_call_count
        st.steps += rec.steps
        st.elapsed_seconds += rec.elapsed_seconds
        st.tests_passed += rec.tests_passed
        st.tests_total += rec.tests_total
        if rec.tests_total or rec.tests_passed:
            st.graded += 1
        if rec.evaluation_status == policy.RESOLVED:
            st.resolved += 1
        elif rec.evaluation_status == policy.UNRESOLVED:
            st.unresolved += 1
        elif rec.evaluation_status == policy.INFRASTRUCTURE_ERROR:
            st.infrastructure_errors += 1
        else:
            st.not_evaluated += 1
    for name, tasks in seen_tasks.items():
        stats[name].tasks = len(tasks)
    return dict(sorted(stats.items()))


def _task_rates(records: Iterable[RunRecord], condition: str) -> dict[str, float]:
    """Resolved rate per task for one condition (counted attempts only)."""
    resolved: dict[str, int] = {}
    counted: dict[str, int] = {}
    for rec in records:
        if rec.condition != condition:
            continue
        if rec.evaluation_status not in policy.COUNTED_STATUSES:
            continue
        counted[rec.instance_id] = counted.get(rec.instance_id, 0) + 1
        if rec.evaluation_status == policy.RESOLVED:
            resolved[rec.instance_id] = resolved.get(rec.instance_id, 0) + 1
    return {task: resolved.get(task, 0) / total for task, total in counted.items()}


def paired_effect(
    records: list[RunRecord],
    condition: str,
    reference: str,
    *,
    n_resamples: int = 5000,
    seed: int = 20261015,
) -> Optional[Effect]:
    """Task-level bootstrap CI for ``rate(condition) - rate(reference)``."""
    cond = _task_rates(records, condition)
    ref = _task_rates(records, reference)
    shared = sorted(set(cond) & set(ref))
    if not shared:
        return None
    diffs = [cond[t] - ref[t] for t in shared]
    point = sum(diffs) / len(diffs)

    rng = random.Random(seed)
    n = len(diffs)
    means: list[float] = []
    for _ in range(n_resamples):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * n_resamples)]
    hi = means[min(n_resamples - 1, int(0.975 * n_resamples))]
    return Effect(
        contrast=f"{condition} - {reference}",
        condition=condition,
        reference=reference,
        diff=point,
        ci_low=lo,
        ci_high=hi,
        n_tasks=n,
        n_resamples=n_resamples,
    )


def analyze(
    records: list[RunRecord],
    *,
    reference: Optional[str] = None,
    n_resamples: int = 5000,
    seed: int = 20261015,
) -> dict[str, Any]:
    """Full summary document for a set of run records."""
    stats = condition_stats(records)
    conditions = list(stats)
    if reference is None:
        reference = conditions[0] if conditions else ""
    effects = []
    for cond in conditions:
        if cond == reference:
            continue
        eff = paired_effect(records, cond, reference, n_resamples=n_resamples, seed=seed)
        if eff is not None:
            effects.append(eff)
    return {
        "n_records": len(records),
        "reference": reference,
        "conditions": {name: st.as_dict() for name, st in stats.items()},
        "effects": [e.as_dict() for e in effects],
    }


def load_records(experiment_id: str, base_dir: Optional[Path] = None) -> list[RunRecord]:
    logger = RunLogger(experiment_id, Path(base_dir) if base_dir else paths.RUNS_DIR)
    return logger.load_records()


def render_text(summary: dict[str, Any]) -> str:
    """Human-readable rendering of :func:`analyze` output."""
    lines: list[str] = []
    lines.append(f"records: {summary['n_records']}   reference: {summary['reference']}")
    header = (
        f"{'condition':<22}{'att':>4}{'tasks':>6}{'res':>4}{'unres':>6}"
        f"{'infra':>6}{'rate':>8}{'tok/att':>10}{'sec/att':>9}{'tools/att':>10}"
        f"{'tests':>9}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for name, st in summary["conditions"].items():
        lines.append(
            f"{name:<22}{st['attempts']:>4}{st['tasks']:>6}{st['resolved']:>4}"
            f"{st['unresolved']:>6}{st['infrastructure_errors']:>6}"
            f"{st['resolved_rate']:>8.2f}{st['mean_total_tokens']:>10.0f}"
            f"{st['mean_elapsed_seconds']:>9.0f}{st['mean_tool_calls']:>10.2f}"
            f"{(str(st['total_tests_passed']) + '/' + str(st['total_tests_total'])):>9}"
        )
    if summary["effects"]:
        lines.append("")
        lines.append("paired effects (task-level bootstrap 95% CI):")
        for eff in summary["effects"]:
            lo, hi = eff["ci95"]
            lines.append(
                f"  {eff['contrast']:<30} diff={eff['diff']:+.3f}  "
                f"95% CI [{lo:+.3f}, {hi:+.3f}]  tasks={eff['n_tasks']}"
            )
    return "\n".join(lines)
