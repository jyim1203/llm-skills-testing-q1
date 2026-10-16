"""The three experimental conditions.

A condition is a pure function from a task + workspace to a
:class:`SessionSpec` (system prompt, tool set, task message, and metadata).
Conditions own *nothing* at runtime except the per-run skill directory they are
given; they never touch shared state, which is what keeps A/B/C isolated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..config import ConditionConfig
from ..models.types import Message, ToolSpec
from ..skills import SkillDoc, sha256_text


@dataclass
class ConditionAssets:
    """Shared, condition-independent and condition-specific text, loaded once."""

    base_system_prompt: str
    workflow_instructions: str
    skill: Optional[SkillDoc] = None


@dataclass
class ConditionContext:
    """Per-attempt, fully isolated inputs."""

    task: Any  # benchmark.TaskInstance
    workspace: Path
    skills_dir: Path


@dataclass
class SessionSpec:
    condition_name: str
    system_prompt: str
    tools: list[ToolSpec]
    task_prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def initial_messages(self) -> list[Message]:
        return [Message.system(self.system_prompt), Message.user(self.task_prompt)]


def render_task_prompt(task: Any) -> str:
    """The condition-independent task message (identical across A/B/C)."""
    hints = (getattr(task, "hints_text", "") or "").strip()
    hints_block = f"\n\nAdditional hints:\n{hints}\n" if hints else ""
    return (
        f"Resolve the following issue in the repository.\n\n"
        f"Repository: {task.repo}\n"
        f"Base commit: {task.base_commit}\n\n"
        f"<issue>\n{task.problem_statement.strip()}\n</issue>"
        f"{hints_block}\n"
        f"When you are finished, stop calling tools. Your edits will be captured "
        f"as a patch and evaluated against the repository's tests."
    )


class Condition(ABC):
    """Base class for experimental conditions."""

    name: str = "condition"

    def __init__(self, config: ConditionConfig, assets: ConditionAssets) -> None:
        self.config = config
        self.assets = assets

    @abstractmethod
    def build(self, ctx: ConditionContext) -> SessionSpec:
        """Produce the session specification for this attempt."""

    # -- shared helpers ----------------------------------------------------- #
    def _base_system_prompt(self) -> str:
        return self.assets.base_system_prompt.strip()

    def _instruction_hash(self) -> Optional[str]:
        if not self.assets.workflow_instructions:
            return None
        return sha256_text(self.assets.workflow_instructions.strip())


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
def get_condition(config: ConditionConfig, assets: ConditionAssets) -> Condition:
    # Imported here to avoid circular imports at module load.
    from .baseline import BaselineCondition
    from .prompt_instructions import PromptInstructionsCondition
    from .skill import SkillCondition

    mapping = {
        "baseline": BaselineCondition,
        "prompt_instructions": PromptInstructionsCondition,
        "skill": SkillCondition,
    }
    try:
        cls = mapping[config.impl]
    except KeyError:
        raise ValueError(
            f"Unknown condition impl {config.impl!r}. Known: {sorted(mapping)}"
        ) from None
    return cls(config, assets)


__all__ = [
    "Condition",
    "ConditionAssets",
    "ConditionContext",
    "SessionSpec",
    "get_condition",
    "render_task_prompt",
]
