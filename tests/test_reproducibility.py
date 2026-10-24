"""Reproducibility anchors.

The scientific claim needs two things frozen: the *task data* (a content hash
over the exact instance definitions) and the *environment* (pinned dataset
revision + recorded image digest). These tests guard the plumbing that records
them into the run log.
"""

from __future__ import annotations

import csv
import json

from skills_experiment.benchmark.swebench_lite import TaskInstance, instances_manifest


def _task(instance_id: str = "fake__fake-1", problem: str = "x") -> TaskInstance:
    return TaskInstance(
        instance_id=instance_id,
        repo="fake/fake",
        base_commit="0" * 40,
        problem_statement=problem,
        hints_text="",
    )


def test_manifest_is_order_independent():
    a, b = _task("fake__a-1", "one"), _task("fake__b-2", "two")
    assert instances_manifest([a, b])["hash"] == instances_manifest([b, a])["hash"]


def test_manifest_changes_with_content():
    h1 = instances_manifest([_task(problem="one")])["hash"]
    h2 = instances_manifest([_task(problem="two")])["hash"]
    assert h1 != h2


def test_manifest_is_stable_for_identical_content():
    h1 = instances_manifest([_task(problem="same")])["hash"]
    h2 = instances_manifest([_task(problem="same")])["hash"]
    assert h1 == h2


def test_local_selection_adds_pytest_task():
    from skills_experiment.benchmark.selection import LOCAL_TASKS, build_selection

    doc = build_selection(subset="local", dataset_revision="abc123")
    ids = [t["instance_id"] for t in doc["tasks"]]
    assert doc["num_tasks"] == 6
    assert len(ids) == len(LOCAL_TASKS)
    assert ids[-1] == "pytest-dev__pytest-5495"
    assert "medium-proxy" in doc["selection_procedure"]
    assert doc["dataset_revision"] == "abc123"


def test_local_main_configs_use_six_task_selection():
    from skills_experiment.config import load_experiment

    full = load_experiment("main-local")
    pilot = load_experiment("main-local-pilot")
    assert full.dataset.selection_file == "data/task_selection_local.json"
    assert full.repeats == 10
    assert pilot.repeats == 1
    assert full.agent.base_system_prompt == "base_system_prompt_minimal.md"
    assert full.condition_options["C_skill"]["require_load"] is True


def test_resume_skips_completed_attempts(tmp_path, fake_task):
    from skills_experiment.config import load_experiment
    from skills_experiment.runner import ExperimentRunner

    config = load_experiment("pilot")
    config.repeats = 1
    runner = ExperimentRunner(config, dry_run=True, base_dir=tmp_path / "runs")
    runner._load_tasks = lambda: [{"task": fake_task, "topic": "t", "why": ""}]

    first = runner.run()
    assert first.completed == 3  # three conditions, one repeat
    second = runner.run(resume=True)
    assert second.completed == 0
    rows = list(csv.DictReader(runner.logger.csv_path.open(encoding="utf-8")))
    assert len(rows) == 3


def test_run_log_carries_provenance(tmp_path, fake_task):
    from skills_experiment.config import load_experiment
    from skills_experiment.runner import ExperimentRunner

    config = load_experiment("pilot")
    runner = ExperimentRunner(config, dry_run=True, base_dir=tmp_path / "runs")
    runner._load_tasks = lambda: [{"task": fake_task, "topic": "t", "why": ""}]
    runner.run()

    manifest = json.loads(
        (runner.logger.base_dir / "dataset_manifest.json").read_text(encoding="utf-8")
    )
    rows = list(csv.DictReader(runner.logger.csv_path.open(encoding="utf-8")))
    assert rows

    # The dataset revision is pinned to a sha, not the mutable branch name.
    assert config.dataset.revision not in ("", "main")

    for row in rows:
        assert row["benchmark_dataset_hash"] == manifest["hash"]
        assert row["benchmark_dataset_revision"] == config.dataset.revision
        assert int(row["seed"]) == config.seed
        assert row["started_at"]
        assert row["framework_git_commit"]
        # Non-docker (mock) runs record no image digest, but the column exists.
        assert "docker_image_digest" in row
