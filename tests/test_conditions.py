"""Condition construction + fairness tests."""

from __future__ import annotations

from pathlib import Path

from skills_experiment import paths
from skills_experiment.config import load_condition_configs
from skills_experiment.conditions import (
    ConditionAssets,
    ConditionContext,
    get_condition,
)
from skills_experiment.skills import ensure_skill_built, parse_front_matter


def _assets() -> ConditionAssets:
    base = (paths.PROMPTS_DIR / "base_system_prompt.md").read_text(encoding="utf-8")
    workflow = (paths.PROMPTS_DIR / "workflow_instructions.md").read_text(encoding="utf-8")
    skill = ensure_skill_built(workflow)
    return ConditionAssets(base_system_prompt=base, workflow_instructions=workflow, skill=skill)


def _build(name: str, task, workspace: Path):
    assets = _assets()
    config = load_condition_configs([name])[0]
    condition = get_condition(config, assets)
    ctx = ConditionContext(task=task, workspace=workspace, skills_dir=workspace / "skills")
    return condition.build(ctx), assets


def test_baseline_has_no_workflow_and_no_skill(fake_task, tmp_path):
    spec, assets = _build("A_baseline", fake_task, tmp_path / "a")
    assert "load_skill" not in {t.name for t in spec.tools}
    assert assets.workflow_instructions.strip() not in spec.system_prompt
    assert spec.metadata["instructions_hash"] is None


def test_prompt_condition_injects_exact_workflow_text(fake_task, tmp_path):
    spec, assets = _build("B_prompt_instructions", fake_task, tmp_path / "b")
    assert assets.workflow_instructions.strip() in spec.system_prompt
    assert "load_skill" not in {t.name for t in spec.tools}
    assert spec.metadata["instructions_hash"] == assets.skill.body_hash


def test_skill_condition_exposes_metadata_not_body(fake_task, tmp_path):
    workspace = tmp_path / "c"
    spec, assets = _build("C_skill", fake_task, workspace)
    tool_names = {t.name for t in spec.tools}
    assert "load_skill" in tool_names
    # metadata (name + description) is advertised ...
    assert assets.skill.name in spec.system_prompt
    assert assets.skill.description in spec.system_prompt
    # ... but the full instructions are NOT pasted into the prompt.
    assert assets.workflow_instructions.strip() not in spec.system_prompt
    # the skill file lives in this attempt's own skills dir
    skill_path = workspace / "skills" / "python_repo_maintenance" / "SKILL.md"
    assert skill_path.exists()
    meta, body = parse_front_matter(skill_path.read_text(encoding="utf-8"))
    assert meta["name"] == assets.skill.name
    assert body.strip() == assets.workflow_instructions.strip()


def test_fairness_b_and_c_share_instruction_text():
    assets = _assets()
    configs = {c.name: c for c in load_condition_configs(["B_prompt_instructions", "C_skill"])}
    assert configs["B_prompt_instructions"].instructions_file == configs["C_skill"].instructions_file
    assert assets.skill.body.strip() == assets.workflow_instructions.strip()


def test_skill_condition_require_load_override(fake_task, tmp_path):
    """A study can require the load call without changing the frozen default."""
    assets = _assets()
    config = load_condition_configs(
        ["C_skill"], overrides={"C_skill": {"require_load": True}}
    )[0]
    assert config.require_load is True
    condition = get_condition(config, assets)
    ctx = ConditionContext(
        task=fake_task, workspace=tmp_path / "c", skills_dir=tmp_path / "c" / "skills"
    )
    spec = condition.build(ctx)
    assert "MUST call" in spec.system_prompt
    assert "load_skill" in spec.system_prompt
    assert spec.metadata["require_load"] is True


def test_skill_condition_default_keeps_metadata_only_wording(fake_task, tmp_path):
    assets = _assets()
    config = load_condition_configs(["C_skill"])[0]
    assert config.require_load is False
    condition = get_condition(config, assets)
    ctx = ConditionContext(
        task=fake_task, workspace=tmp_path / "c", skills_dir=tmp_path / "c" / "skills"
    )
    spec = condition.build(ctx)
    assert "MUST call" not in spec.system_prompt
    assert spec.metadata["require_load"] is False


def test_unknown_condition_override_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="Unknown condition option"):
        load_condition_configs(["C_skill"], overrides={"C_skill": {"nope": True}})


def test_local_experiment_requires_skill_load_but_frozen_pilot_does_not():
    from skills_experiment.config import load_experiment

    assert load_experiment("pilot").condition_options == {}
    assert load_experiment("pilot-local").condition_options == {
        "C_skill": {"require_load": True}
    }


