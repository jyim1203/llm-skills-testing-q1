"""Run-plan ordering and parallel dry-run execution."""

from __future__ import annotations

import csv
import json
from collections import Counter

from skills_experiment.config import load_experiment
from skills_experiment.runner import ExperimentRunner


def _runner(tmp_path, fake_task, *, repeats: int, workers: int, seed: int = 20261015):
    config = load_experiment("pilot")
    config.repeats = repeats
    config.workers = workers
    config.seed = seed
    runner = ExperimentRunner(config, dry_run=True, base_dir=tmp_path / "runs")
    runner._load_tasks = lambda: [{"task": fake_task, "topic": "t", "why": ""}]
    return runner


def test_plan_is_repeat_major_and_condition_balanced(tmp_path, fake_task):
    runner = _runner(tmp_path, fake_task, repeats=3, workers=2)
    tasks = ["task-a", "task-b", "task-c"]
    plan = runner.build_plan(tasks)

    assert len(plan) == len(tasks) * runner.config.repeats * len(runner.config.conditions)
    assert [item.attempt for item in plan] == sorted(item.attempt for item in plan)

    per_repeat = len(tasks) * len(runner.config.conditions)
    for repeat in range(1, runner.config.repeats + 1):
        block = plan[(repeat - 1) * per_repeat : repeat * per_repeat]
        assert {item.attempt for item in block} == {repeat}
        for task in tasks:
            conditions = [item.condition for item in block if item.instance_id == task]
            assert Counter(conditions) == Counter(runner.config.conditions)


def test_plan_seed_controls_order_reproducibly(tmp_path, fake_task):
    tasks = ["task-a", "task-b", "task-c"]
    first = _runner(tmp_path, fake_task, repeats=2, workers=2, seed=11).build_plan(tasks)
    second = _runner(tmp_path, fake_task, repeats=2, workers=2, seed=11).build_plan(tasks)
    different = _runner(tmp_path, fake_task, repeats=2, workers=2, seed=12).build_plan(tasks)

    assert [(i.instance_id, i.condition, i.attempt) for i in first] == [
        (i.instance_id, i.condition, i.attempt) for i in second
    ]
    assert [(i.instance_id, i.condition, i.attempt) for i in first] != [
        (i.instance_id, i.condition, i.attempt) for i in different
    ]


def test_parallel_dry_run_writes_every_attempt_and_plan(tmp_path, fake_task):
    runner = _runner(tmp_path, fake_task, repeats=2, workers=2)
    summary = runner.run()

    expected = len(runner.config.conditions) * runner.config.repeats
    assert summary.planned == expected
    assert summary.completed == expected
    assert summary.workers == 2
    assert summary.infrastructure_errors == 0

    rows = list(csv.DictReader(runner.logger.csv_path.open(encoding="utf-8")))
    assert len(rows) == expected
    assert len({(r["instance_id"], r["condition"], r["attempt_number"]) for r in rows}) == expected

    plan = json.loads((runner.logger.base_dir / "plan.json").read_text(encoding="utf-8"))
    assert plan["seed"] == runner.config.seed
    assert plan["workers"] == 2
    assert plan["planned"] == expected
    assert len(plan["items"]) == expected
