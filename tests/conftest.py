"""Shared pytest configuration: make the src layout importable without install."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402


@pytest.fixture
def fake_task():
    from skills_experiment.benchmark.swebench_lite import TaskInstance

    return TaskInstance(
        instance_id="fake__fake-1",
        repo="fake/fake",
        base_commit="0" * 40,
        problem_statement="The `add` function returns the wrong value.",
        hints_text="",
    )
