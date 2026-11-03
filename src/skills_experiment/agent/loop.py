"""Minimal tool-using agent loop.

Deliberately small and explicit so that the *only* differences between
conditions are the ones the conditions introduce (system prompt / skill
exposure). Everything else -- tool set, step budget, stop conditions -- is
shared and lives here.

The loop is synchronous and provider-agnostic: it talks only to
:class:`~skills_experiment.models.base.ModelClient`.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from ..models.base import ModelClient
from ..models.types import Message, Usage
from ..observability import EventSink, emit, sha256_text
from .tools import ToolExecutor


@dataclass
class AgentResult:
    patch: str = ""
    messages: list[Message] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    tool_call_count: int = 0
    elapsed_seconds: float = 0.0
    steps: int = 0
    stop_reason: str = ""
    skill_discovered: bool = False
    skill_loaded: bool = False
    errors: list[str] = field(default_factory=list)


class AgentLoop:
    def __init__(
        self,
        model: ModelClient,
        executor: ToolExecutor,
        *,
        max_steps: int = 40,
        max_tokens: int = 120_000,
        elapsed_seconds: int = 1800,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.model = model
        self.executor = executor
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.elapsed_seconds = elapsed_seconds
        self.event_sink = event_sink

    def run(self, spec, task=None) -> AgentResult:
        """Run the loop against a :class:`SessionSpec` and capture the patch."""
        start = time.time()
        messages: list[Message] = spec.initial_messages()
        usage = Usage()
        tool_call_count = 0
        skill_loaded = False
        stop_reason = "max_steps"
        steps = 0
        errors: list[str] = []

        emit(
            self.event_sink,
            "run_start",
            condition=spec.condition_name,
            system_prompt_chars=len(spec.system_prompt),
            task_prompt_chars=len(spec.task_prompt),
            system_prompt_sha256=sha256_text(spec.system_prompt),
            tool_names=[tool.name for tool in spec.tools],
            max_steps=self.max_steps,
            max_tokens=self.max_tokens,
            elapsed_seconds=self.elapsed_seconds,
        )

        for step in range(self.max_steps):
            steps = step + 1
            if time.time() - start > self.elapsed_seconds:
                stop_reason = "elapsed_budget"
                break

            call_started = time.perf_counter()
            response = self.model.complete(messages, tools=spec.tools)
            call_latency_ms = round((time.perf_counter() - call_started) * 1000, 3)
            usage += response.usage
            emit(
                self.event_sink,
                "model_call",
                step=steps,
                latency_ms=call_latency_ms,
                model_id=response.model_id,
                finish_reason=response.stop_reason,
                tool_call_count=len(response.tool_calls),
                tool_names=[call.name for call in response.tool_calls],
                text_chars=len(response.text or ""),
                reasoning_chars=len(response.reasoning_content or ""),
                messages_count=len(messages),
                usage=asdict(response.usage),
            )
            messages.append(response.to_message())

            if response.wants_tools:
                for call in response.tool_calls:
                    tool_call_count += 1
                    self.executor.current_step = steps
                    outcome = self.executor.execute(call)
                    if outcome.skill_loaded:
                        skill_loaded = True
                    messages.append(
                        Message.tool_result(call.id, outcome.content, name=call.name)
                    )
                    if outcome.error:
                        errors.append(f"{call.name}: {outcome.error}")
            else:
                stop_reason = response.stop_reason or "completed"
                break

            if usage.total_tokens >= self.max_tokens:
                stop_reason = "token_budget"
                break

        patch = self.executor.sandbox.diff()
        skill_discovered = any(e.get("tool") == "load_skill" for e in self.executor.events)
        elapsed_seconds = time.time() - start
        emit(
            self.event_sink,
            "run_end",
            steps=steps,
            stop_reason=stop_reason,
            tool_call_count=tool_call_count,
            patch_chars=len(patch),
            skill_discovered=skill_discovered,
            skill_loaded=skill_loaded,
            errors=errors,
            usage=asdict(usage),
            elapsed_seconds=round(elapsed_seconds, 3),
        )
        return AgentResult(
            patch=patch,
            messages=messages,
            usage=usage,
            tool_call_count=tool_call_count,
            elapsed_seconds=elapsed_seconds,
            steps=steps,
            stop_reason=stop_reason,
            skill_discovered=skill_discovered,
            skill_loaded=skill_loaded,
            errors=errors,
        )
