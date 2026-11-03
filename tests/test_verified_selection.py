"""Frozen Verified task-set invariants."""

from __future__ import annotations

import json
from collections import Counter

from skills_experiment import paths


def _selection() -> dict:
    return json.loads(
        (paths.DATA_DIR / "task_selection_verified.json").read_text(encoding="utf-8")
    )


def test_verified_selection_is_balanced_and_one_per_repo():
    data = _selection()
    tasks = data["tasks"]
    assert data["num_tasks"] == len(tasks) == 10
    assert len({t["instance_id"] for t in tasks}) == 10
    assert len({t["repo"] for t in tasks}) == 10
    assert Counter(t["tier"] for t in tasks) == {
        "easy": 2,
        "medium": 3,
        "hard": 4,
        "hard_gt4h": 1,
    }


def test_verified_selection_does_not_reuse_lite_ids():
    verified = {t["instance_id"] for t in _selection()["tasks"]}
    lite = json.loads(
        (paths.DATA_DIR / "task_selection_local.json").read_text(encoding="utf-8")
    )
    assert verified.isdisjoint({t["instance_id"] for t in lite["tasks"]})


def test_verified_configs_are_pinned_and_use_two_workers():
    from skills_experiment.config import load_experiment

    pilot = load_experiment("verified-pilot")
    main = load_experiment("verified-main")
    assert pilot.dataset.name == "SWE-bench/SWE-bench_Verified"
    assert main.dataset.name == "SWE-bench/SWE-bench_Verified"
    assert pilot.repeats == 1
    assert main.repeats == 8
    assert pilot.workers == main.workers == 2
    assert pilot.dataset.revision == main.dataset.revision == _selection()["dataset_revision"]
