"""Isolation + end-to-end dry-run tests.

These verify the core claim of the scaffolding: each attempt is independent,
and the skill only exists inside Condition C's own workspace.
"""

from __future__ import annotations

import csv

from skills_experiment.config import load_experiment
from skills_experiment.runner import ExperimentRunner


def _dry_run_runner(tmp_path, fake_task):
    config = load_experiment("pilot")
    runner = ExperimentRunner(config, dry_run=True, base_dir=tmp_path / "runs")
    # Avoid touching the network / dataset cache.
    runner._load_tasks = lambda: [{"task": fake_task, "topic": "test", "why": "test"}]
    return runner


def test_fairness_hashes_match(tmp_path, fake_task):
    runner = _dry_run_runner(tmp_path, fake_task)
    assets = runner._load_assets()
    fairness = runner.verify_fairness(assets)
    assert fairness["B"] == fairness["C"]


def test_dry_run_produces_three_isolated_attempts(tmp_path, fake_task):
    runner = _dry_run_runner(tmp_path, fake_task)
    summary = runner.run()

    assert summary.planned == 3
    assert summary.completed == 3
    assert summary.infrastructure_errors == 0

    # one CSV row per attempt
    rows = list(csv.DictReader((runner.logger.csv_path).open(encoding="utf-8")))
    assert len(rows) == 3
    conditions = {r["condition"] for r in rows}
    assert conditions == {"A_baseline", "B_prompt_instructions", "C_skill"}

    inst = fake_task.instance_id
    a_dir = runner.logger.workspace_dir(inst, "A_baseline", 1)
    c_dir = runner.logger.workspace_dir(inst, "C_skill", 1)

    # distinct workspaces
    assert a_dir != c_dir
    # the skill exists ONLY under condition C's workspace
    assert not (a_dir / "skills").exists()
    assert (c_dir / "skills" / "python_repo_maintenance" / "SKILL.md").exists()


def test_skill_loaded_only_in_skill_condition(tmp_path, fake_task):
    runner = _dry_run_runner(tmp_path, fake_task)
    summary = runner.run()
    by_condition = {r.condition: r for r in summary.records}
    assert by_condition["C_skill"].skill_loaded is True
    assert by_condition["A_baseline"].skill_loaded is False
    assert by_condition["B_prompt_instructions"].skill_loaded is False
