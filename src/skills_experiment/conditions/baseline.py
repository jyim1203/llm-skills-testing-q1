"""Condition A -- Baseline.

Task + repository context only. No experimental workflow instructions and no
skill. This anchors the comparison.
"""

from __future__ import annotations

from ..agent.tools import base_tool_specs
from .base import Condition, ConditionContext, SessionSpec, render_task_prompt


class BaselineCondition(Condition):
    name = "A_baseline"

    def build(self, ctx: ConditionContext) -> SessionSpec:
        return SessionSpec(
            condition_name=self.config.name,
            system_prompt=self._base_system_prompt(),
            tools=base_tool_specs(),
            task_prompt=render_task_prompt(ctx.task),
            metadata={
                "impl": "baseline",
                "instructions_file": None,
                "instructions_hash": None,
                "skill_enabled": False,
            },
        )
