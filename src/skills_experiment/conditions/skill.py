"""Condition C -- Skill.

The same workflow content as Condition B, but packaged as ``SKILL.md`` and
delivered through a skill mechanism. Only the skill's ``name`` and
``description`` metadata are advertised up front; the full body is available
only if the agent calls the ``load_skill`` tool.

The skill file is written into this attempt's own ``skills_dir`` (under the run
workspace), so it cannot leak into Conditions A or B, which never receive a
skills directory or the ``load_skill`` tool.
"""

from __future__ import annotations

from pathlib import Path

from ..agent.tools import base_tool_specs, load_skill_tool_spec
from ..skills import write_skill_md
from .base import Condition, ConditionContext, SessionSpec, render_task_prompt


class SkillCondition(Condition):
    name = "C_skill"

    def build(self, ctx: ConditionContext) -> SessionSpec:
        skill = self.assets.skill
        if skill is None:
            raise ValueError("Condition C requires a skill asset; none was provided.")

        skill_slug = self.config.skill_dir or "python_repo_maintenance"
        run_skill_dir = Path(ctx.skills_dir) / skill_slug
        skill_path = write_skill_md(skill, run_skill_dir)

        system_prompt = (
            f"{self._base_system_prompt()}\n\n"
            f"# Skills\n\n"
            f"You have access to skills: reusable sets of instructions you can load "
            f"on demand. A skill's name and description are shown below; call the "
            f"`load_skill` tool with the skill's name to load its full instructions "
            f"before you begin work that it covers.\n\n"
            f"Available skills:\n"
            f"- {skill.name}: {skill.description}"
        )

        tools = base_tool_specs() + [load_skill_tool_spec([skill.name])]
        return SessionSpec(
            condition_name=self.config.name,
            system_prompt=system_prompt,
            tools=tools,
            task_prompt=render_task_prompt(ctx.task),
            metadata={
                "impl": "skill",
                "instructions_file": self.config.instructions_file,
                "instructions_hash": self._instruction_hash(),
                "skill_name": skill.name,
                "skill_description": skill.description,
                "skill_body_hash": skill.body_hash,
                "skill_path": str(skill_path),
                "skill_enabled": True,
            },
        )
