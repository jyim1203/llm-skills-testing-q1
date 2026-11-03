"""Tests for structured event logging and loop instrumentation."""

from __future__ import annotations

import json

from skills_experiment.agent.loop import AgentLoop
from skills_experiment.agent.tools import ToolExecutor, base_tool_specs
from skills_experiment.conditions.base import SessionSpec
from skills_experiment.models.mock import MockModelClient
from skills_experiment.models.types import ModelResponse, ToolCall, Usage
from skills_experiment.observability import EventRecorder
from skills_experiment.sandbox.noop import NoopSandbox


def test_event_recorder_includes_base_fields(tmp_path):
    path = tmp_path / "events.jsonl"
    recorder = EventRecorder(path, base={"attempt_id": "a1", "condition": "C"})
    recorder("run_start", {"max_steps": 3})
    recorder.close()

    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["event"] == "run_start"
    assert row["attempt_id"] == "a1"
    assert row["condition"] == "C"
    assert row["max_steps"] == 3
    assert "timestamp" in row


def test_agent_loop_emits_model_and_tool_events(tmp_path):
    events: list[tuple[str, dict]] = []
    sandbox = NoopSandbox(tmp_path)
    script = [
        ModelResponse(
            text="",
            tool_calls=[
                ToolCall(
                    id="c1",
                    name="write_file",
                    arguments={"path": "pkg/module.py", "content": "def add(a, b):\n    return a + b\n"},
                )
            ],
            usage=Usage(input_tokens=10, output_tokens=5),
        ),
        ModelResponse(
            text="",
            tool_calls=[
                ToolCall(
                    id="c2",
                    name="run_shell",
                    arguments={"command": "python -m pytest pkg/test_module.py -q"},
                )
            ],
            usage=Usage(input_tokens=8, output_tokens=4),
        ),
        ModelResponse(text="done", usage=Usage(input_tokens=3, output_tokens=2), stop_reason="stop"),
    ]
    spec = SessionSpec(
        condition_name="C_skill",
        system_prompt="sys",
        tools=base_tool_specs(),
        task_prompt="do the thing",
    )
    executor = ToolExecutor(
        sandbox=sandbox,
        event_sink=lambda event, fields: events.append((event, fields)),
    )
    result = AgentLoop(
        MockModelClient(script=script),
        executor,
        max_steps=5,
        event_sink=lambda event, fields: events.append((event, fields)),
    ).run(spec)

    names = [event for event, _ in events]
    assert names[0] == "run_start"
    assert names[-1] == "run_end"
    assert names.count("model_call") == 3
    assert names.count("tool_call") == 2

    tool_events = [fields for event, fields in events if event == "tool_call"]
    assert tool_events[0]["tool"] == "write_file"
    assert tool_events[0]["exit_code"] == 0
    assert "content" not in tool_events[0]["arguments"]
    assert tool_events[1]["tool"] == "run_shell"
    assert tool_events[1]["arguments"]["command"].startswith("python -m pytest")

    model_events = [fields for event, fields in events if event == "model_call"]
    assert model_events[0]["usage"]["input_tokens"] == 10
    assert model_events[0]["reasoning_chars"] == 0
    assert result.tool_call_count == 2
