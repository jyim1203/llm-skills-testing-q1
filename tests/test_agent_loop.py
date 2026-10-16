"""Agent loop tests using the deterministic mock client and noop sandbox."""

from __future__ import annotations

from skills_experiment.agent.loop import AgentLoop
from skills_experiment.agent.tools import ToolExecutor, base_tool_specs
from skills_experiment.conditions.base import SessionSpec
from skills_experiment.models.mock import MockModelClient
from skills_experiment.models.types import ModelResponse, ToolCall, Usage
from skills_experiment.sandbox.noop import NoopSandbox


def _spec() -> SessionSpec:
    return SessionSpec(
        condition_name="test",
        system_prompt="sys",
        tools=base_tool_specs(),
        task_prompt="do the thing",
    )


def test_loop_executes_tools_and_captures_patch(tmp_path):
    sandbox = NoopSandbox(tmp_path)
    script = [
        ModelResponse(
            text="",
            tool_calls=[
                ToolCall(
                    id="c1",
                    name="write_file",
                    arguments={"path": "pkg/module.py", "content": "def add(a, b):\n    return a + b + 0\n"},
                )
            ],
            usage=Usage(input_tokens=10, output_tokens=5),
        ),
        ModelResponse(text="done", usage=Usage(input_tokens=3, output_tokens=2), stop_reason="stop"),
    ]
    client = MockModelClient(script=script)
    executor = ToolExecutor(sandbox=sandbox, skills_dir=None)
    result = AgentLoop(client, executor, max_steps=5).run(_spec())

    assert "return a + b + 0" in result.patch
    assert result.tool_call_count == 1
    assert result.steps == 2
    assert result.usage.total_tokens == 20
    assert result.stop_reason == "stop"


def test_loop_respects_token_budget(tmp_path):
    sandbox = NoopSandbox(tmp_path)
    # Always request a tool so the loop would otherwise run to max_steps.
    script = [
        ModelResponse(
            text="",
            tool_calls=[ToolCall(id=f"c{i}", name="list_dir", arguments={})],
            usage=Usage(input_tokens=100, output_tokens=100),
        )
        for i in range(10)
    ]
    client = MockModelClient(script=script)
    executor = ToolExecutor(sandbox=sandbox)
    result = AgentLoop(client, executor, max_steps=10, max_tokens=250).run(_spec())
    assert result.stop_reason == "token_budget"
    assert result.usage.total_tokens >= 250


def test_default_mock_discovers_and_loads_skill(tmp_path):
    """The mock exercises Condition C's discovery path when a skill is present."""
    from skills_experiment.agent.tools import load_skill_tool_spec
    from skills_experiment.skills import ensure_skill_built

    skills_dir = tmp_path / "skills"
    ensure_skill_built(
        "Step 1. Inspect.\nStep 2. Fix.\n", skill_dir=skills_dir / "python_repo_maintenance"
    )
    spec = SessionSpec(
        condition_name="C_skill",
        system_prompt="You have skills.",
        tools=base_tool_specs() + [load_skill_tool_spec(["python-repo-maintenance"])],
        task_prompt="do the thing",
    )
    sandbox = NoopSandbox(tmp_path)
    executor = ToolExecutor(sandbox=sandbox, skills_dir=skills_dir)
    result = AgentLoop(MockModelClient(), executor, max_steps=5).run(spec)

    assert result.skill_discovered is True
    assert result.skill_loaded is True
