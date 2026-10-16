"""Grading orchestration: capture -> harness -> run-log update.

Attempts are grouped by ``(condition, attempt_number)`` so a single harness run
grades every instance for that group at once (one container per instance). Each
group gets its own ``run_id`` and predictions file.

Updates are written back to ``runs.jsonl``/``runs.csv`` in place, so the run log
is the single record of truth for the whole experiment.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .. import paths
from ..config import ExperimentConfig
from ..runlog.records import RunLogger, RunRecord
from . import policy
from .harness import (
    HarnessError,
    HarnessResult,
    Prediction,
    harness_version,
    resolve_harness_python,
    run_harness,
    write_predictions,
)


@dataclass
class GradeSummary:
    experiment_id: str
    groups: int = 0
    graded_attempts: int = 0
    resolved: int = 0
    unresolved: int = 0
    infrastructure_errors: int = 0
    tests_passed: int = 0
    tests_total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    harness_version: str = ""
    report_paths: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "groups": self.groups,
            "graded_attempts": self.graded_attempts,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "infrastructure_errors": self.infrastructure_errors,
            "tests_passed": self.tests_passed,
            "tests_total": self.tests_total,
            "by_status": self.by_status,
            "harness_version": self.harness_version,
        }


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text.replace("/", "__"))


def _patch_text(record: RunRecord) -> str:
    if not record.patch_path:
        return ""
    path = Path(record.patch_path)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def grade_experiment(
    config: ExperimentConfig,
    *,
    base_dir: Optional[Path] = None,
    only_missing: bool = True,
    condition: Optional[str] = None,
    attempt: Optional[int] = None,
    max_workers: int = 4,
    timeout: Optional[int] = None,
    subprocess_timeout: Optional[int] = None,
) -> GradeSummary:
    """Grade captured patches with the official harness and update the run log."""
    base = Path(base_dir) if base_dir else paths.RUNS_DIR
    logger = RunLogger(config.id, base)
    records = logger.load_records()
    if not records:
        raise HarnessError(f"No run log found for experiment '{config.id}' under {logger.base_dir}.")

    exp_dir = logger.base_dir
    harness_dir = exp_dir / "harness"
    reports_dir = harness_dir / "reports"
    python = resolve_harness_python(config.harness.python)
    version = harness_version(python)

    # select records to (re)grade
    targets = []
    for record in records:
        if condition and record.condition != condition:
            continue
        if attempt is not None and record.attempt_number != attempt:
            continue
        if only_missing and record.evaluation_status in policy.COUNTED_STATUSES:
            continue
        targets.append(record)

    summary = GradeSummary(experiment_id=config.id, harness_version=version)

    # group by (condition, attempt) so one harness run handles all instances
    groups: dict[tuple[str, int], list[RunRecord]] = {}
    for record in targets:
        groups.setdefault((record.condition, record.attempt_number), []).append(record)

    for (cond, att), group in sorted(groups.items()):
        summary.groups += 1
        run_id = _slug(f"{config.id}-{cond}-a{att}")
        model_name = _slug(f"{config.id}__{cond}__a{att}")
        predictions = [
            Prediction(
                instance_id=rec.instance_id,
                model_name_or_path=model_name,
                model_patch=_patch_text(rec),
            )
            for rec in group
        ]
        pred_path = write_predictions(predictions, harness_dir / "predictions" / f"{run_id}.jsonl")

        # Start from a clean slate: the harness skips instances that already have
        # a report for this run_id, so stale logs would silently be reused.
        stale = harness_dir / "logs" / "run_evaluation" / run_id
        if stale.exists():
            shutil.rmtree(stale, ignore_errors=True)

        result: HarnessResult = run_harness(
            predictions_path=pred_path,
            run_id=run_id,
            dataset=config.dataset.name,
            split=config.dataset.split,
            instance_ids=[rec.instance_id for rec in group],
            python=python,
            max_workers=max_workers,
            timeout=timeout or config.harness.timeout_seconds,
            work_dir=harness_dir,
            report_dir=reports_dir,
            extra_args=config.harness.extra_args,
            subprocess_timeout=subprocess_timeout,
        )
        if result.report_path:
            summary.report_paths.append(str(result.report_path))

        for rec in group:
            classification = policy.classify_harness_result(
                _patch_text(rec), rec.instance_id, result
            )
            rec.evaluation_status = classification.status
            rec.failure_category = classification.category
            rec.harness_version = version
            stats = result.test_stats.get(rec.instance_id) or {}
            rec.tests_passed = int(stats.get("tests_passed", 0))
            rec.tests_total = int(stats.get("tests_total", 0))
            rec.fail_to_pass_passed = int(stats.get("fail_to_pass_passed", 0))
            rec.fail_to_pass_total = int(stats.get("fail_to_pass_total", 0))
            rec.pass_to_pass_passed = int(stats.get("pass_to_pass_passed", 0))
            rec.pass_to_pass_total = int(stats.get("pass_to_pass_total", 0))
            summary.tests_passed += rec.tests_passed
            summary.tests_total += rec.tests_total
            summary.graded_attempts += 1
            summary.by_status[classification.status] = summary.by_status.get(classification.status, 0) + 1
            if classification.status == policy.RESOLVED:
                summary.resolved += 1
            elif classification.status == policy.UNRESOLVED:
                summary.unresolved += 1
            elif classification.status == policy.INFRASTRUCTURE_ERROR:
                summary.infrastructure_errors += 1

    logger.rewrite(records)
    return summary
