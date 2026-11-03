"""Tests for the Harbor/pro-V2 behavior extractor."""

from __future__ import annotations

import json
from pathlib import Path

from skills_experiment.behavior import extract, write_attempts_csv, write_events_csv


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def _make_attempt(tmp_path: Path) -> Path:
    jobs = tmp_path / "jobs"
    job = jobs / "job-test"
    trial = job / "trial-test"
    task_id = "instance_repo__repo-abcdef"
    _write_json(job / "result.json", {"id": "job-test", "stats": {}})
    _write_json(
        trial / "result.json",
        {
            "task_name": f"swebench-pro/{task_id}",
            "trial_name": "trial-test",
            "config": {"job_id": "job-test", "agent": {"kwargs": {"condition": "C", "repeat": 0}}},
            "agent_info": {"name": "skills-experiment", "version": "0.2.0", "model_info": None},
            "agent_result": {
                "n_input_tokens": 100,
                "n_output_tokens": 20,
                "metadata": {
                    "condition": "C_skill",
                    "repeat": 0,
                    "steps": 5,
                    "stop_reason": "stop",
                    "tool_call_count": 4,
                    "skill_loaded": True,
                    "errors": [],
                    "workflow_version": "v3",
                },
            },
            "verifier_result": {"rewards": {"reward": 1.0}},
            "verifier_environment_mode": "shared",
            "exception_info": None,
            "started_at": "2026-11-03T10:00:00Z",
            "finished_at": "2026-11-03T10:01:00Z",
        },
    )
    _write_json(
        trial / "config.json",
        {"task": {"path": f"v2/tasks/{task_id}"}, "agent": {"kwargs": {"condition": "C"}}},
    )
    messages = [
        {"role": "system", "content": "sys", "tool_calls": [], "tool_call_id": None, "name": None, "reasoning_content": None},
        {"role": "user", "content": "issue", "tool_calls": [], "tool_call_id": None, "name": None, "reasoning_content": None},
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "inspect first",
            "tool_calls": [{"id": "c1", "name": "read_file", "arguments": {"path": "test_mod.py"}}],
            "tool_call_id": None,
            "name": None,
        },
        {"role": "tool", "content": "1: def test_x(): pass", "tool_calls": [], "tool_call_id": "c1", "name": "read_file", "reasoning_content": None},
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "run the test",
            "tool_calls": [{"id": "c2", "name": "run_shell", "arguments": {"command": "python -m pytest test_mod.py -q"}}],
            "tool_call_id": None,
            "name": None,
        },
        {"role": "tool", "content": "1 passed", "tool_calls": [], "tool_call_id": "c2", "name": "run_shell", "reasoning_content": None},
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "edit source",
            "tool_calls": [{"id": "c3", "name": "write_file", "arguments": {"path": "pkg/mod.py", "content": "x = 1\n"}}],
            "tool_call_id": None,
            "name": None,
        },
        {"role": "tool", "content": "[ok] wrote 6 bytes to pkg/mod.py", "tool_calls": [], "tool_call_id": "c3", "name": "write_file", "reasoning_content": None},
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "verify",
            "tool_calls": [{"id": "c4", "name": "run_shell", "arguments": {"command": "python -m pytest test_mod.py -q"}}],
            "tool_call_id": None,
            "name": None,
        },
        {"role": "tool", "content": "1 passed", "tool_calls": [], "tool_call_id": "c4", "name": "run_shell", "reasoning_content": None},
        {"role": "assistant", "content": "done", "tool_calls": [], "tool_call_id": None, "name": None, "reasoning_content": "finished"},
    ]
    _write_jsonl(trial / "agent" / "messages.jsonl", messages)
    (trial / "agent" / "patch.diff").write_text(
        "diff --git a/pkg/mod.py b/pkg/mod.py\n"
        "--- a/pkg/mod.py\n"
        "+++ b/pkg/mod.py\n"
        "@@ -1 +1 @@\n"
        "-x = 0\n"
        "+x = 1\n",
        encoding="utf-8",
    )
    _write_json(
        trial / "verifier" / "output.json",
        {
            "tests": [
                {"name": "test_mod.py::test_x", "status": "PASSED"},
                {"name": "test_mod.py::test_y", "status": "PASSED"},
            ]
        },
    )
    dataset = tmp_path / "dataset.json"
    _write_json(
        dataset,
        [
            {
                "instance_id": task_id,
                "fail_to_pass": json.dumps(["test_mod.py::test_x"]),
                "pass_to_pass": json.dumps(["test_mod.py::test_y"]),
            }
        ],
    )
    return tmp_path / "jobs"


def test_extract_behavior_features(tmp_path):
    root = _make_attempt(tmp_path)
    dataset = tmp_path / "dataset.json"
    attempts, events = extract(root, dataset)

    assert len(attempts) == 1
    row = attempts[0]
    assert row["condition"] == "C"
    assert row["repeat"] == 0
    assert row["resolved"] is True
    assert row["f2p_passed"] == 1 and row["f2p_total"] == 1
    assert row["p2p_passed"] == 1 and row["p2p_total"] == 1
    assert row["tool_calls"] == 4
    assert row["edit_calls"] == 1
    assert row["test_calls"] == 2
    assert row["read_before_edit"] is True
    assert row["test_before_edit"] is True
    assert row["test_after_last_edit"] is True
    assert row["verification_rate"] == 1
    assert row["patch_files"] == 1
    assert row["reasoning_chars"] > 0
    assert row["budget_exhausted"] is False
    assert row["skill_loaded"] is True
    assert len(events) == 4


def test_extractor_uses_event_stream_when_present(tmp_path):
    root = _make_attempt(tmp_path)
    trial = root / "job-test" / "trial-test"
    _write_jsonl(
        trial / "agent" / "events.jsonl",
        [
            {"event": "run_start", "timestamp": "2026-11-03T10:00:00+00:00"},
            {
                "event": "model_call",
                "timestamp": "2026-11-03T10:00:01+00:00",
                "step": 1,
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "reasoning_chars": 7,
                "latency_ms": 100,
            },
            {
                "event": "tool_call",
                "timestamp": "2026-11-03T10:00:01+00:00",
                "step": 1,
                "tool": "read_file",
                "arguments": {"path": "test_mod.py"},
                "ok": True,
            },
            {
                "event": "tool_call",
                "timestamp": "2026-11-03T10:00:02+00:00",
                "step": 2,
                "tool": "write_file",
                "arguments": {"path": "pkg/mod.py", "content_chars": 6},
                "ok": True,
            },
            {
                "event": "tool_call",
                "timestamp": "2026-11-03T10:00:03+00:00",
                "step": 3,
                "tool": "run_shell",
                "arguments": {"command": "python -m pytest test_mod.py -q"},
                "ok": True,
                "exit_code": 0,
            },
            {
                "event": "run_end",
                "timestamp": "2026-11-03T10:00:04+00:00",
                "stop_reason": "stop",
            },
        ],
    )
    attempts, _ = extract(root)
    row = attempts[0]
    assert row["events_tool_calls"] == 3
    assert row["events_prompt_tokens"] == 10
    assert row["time_to_first_edit_seconds"] == 2.0
    assert row["time_to_first_test_seconds"] == 3.0
    assert row["verification_rate"] == 1


def test_extractor_writes_csv(tmp_path):
    root = _make_attempt(tmp_path)
    attempts, events = extract(root)
    write_attempts_csv(tmp_path / "attempts.csv", attempts)
    write_events_csv(tmp_path / "events.csv", events)
    assert "attempt_id" in (tmp_path / "attempts.csv").read_text(encoding="utf-8")
    assert "test_calls" in (tmp_path / "attempts.csv").read_text(encoding="utf-8")
    assert "tool" in (tmp_path / "events.csv").read_text(encoding="utf-8")
