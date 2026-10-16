"""Condition B -- Direct prompt instructions.

The complete experimental workflow text is injected straight into the system
prompt. The substantive content is byte-identical to the skill body used by
Condition C; only the delivery mechanism differs (handoff section 5).
"""

from __future__ import annotations

from ..agent.tools import base_tool_specs
from .base import Condition, ConditionContext, SessionSpec, render_task_prompt


class PromptInstructionsCondition(Condition):
    name = "B_prompt_instructions"

    def build(self, ctx: ConditionContext) -> SessionSpec:
        instructions = self.assets.workflow_instructions.strip()
        system_prompt = f"{self._base_system_prompt()}\n\n# Workflow instructions\n\n{instructions}"
        return SessionSpec(
            condition_name=self.config.name,
            system_prompt=system_prompt,
            tools=base_tool_specs(),
            task_prompt=render_task_prompt(ctx.task),
            metadata={
                "impl": "prompt_instructions",
                "instructions_file": self.config.instructions_file,
                "instructions_hash": self._instruction_hash(),
                "injected_chars": len(instructions),
                "skill_enabled": False,
            },
        )
