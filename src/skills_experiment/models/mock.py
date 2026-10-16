"""Deterministic offline model client.

Used for smoke tests, dry runs, and CI. It never touches the network and needs
no credentials, so the full pipeline (conditions -> agent loop -> logging ->
patch capture) can be exercised without spending money.

The default policy is a tiny deterministic state machine:

1. If a ``load_skill`` tool is available and no skill has been loaded yet,
   request the first advertised skill (this exercises Condition C's discovery
   path).
2. Otherwise call ``list_dir`` once, if available.
3. Otherwise emit a final text turn, which ends the loop.

You can override the behavior entirely with an explicit ``script`` of
:class:`ModelResponse` objects (used by the unit tests).
"""

from __future__ import annotations

from typing import Any, Optional

from .base import ModelClient
from .types import Message, ModelResponse, ToolCall, ToolSpec, Usage


def _approx_tokens(text: str) -> int:
    # ~4 characters per token is a serviceable rough estimate for a mock.
    return max(1, len(text) // 4)


class MockModelClient(ModelClient):
    provider = "mock"

    def __init__(
        self,
        model_id: str = "mock-echo",
        params: Optional[dict[str, Any]] = None,
        pricing: Optional[dict[str, float]] = None,
        script: Optional[list[ModelResponse]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_id=model_id, params=params, pricing=pricing, **kwargs)
        self._script: list[ModelResponse] = list(script or [])
        self._cursor = 0
        self.calls: int = 0  # introspection for tests

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSpec]] = None,
    ) -> ModelResponse:
        self.calls += 1

        if self._script:
            resp = self._script[min(self._cursor, len(self._script) - 1)]
            self._cursor += 1
            if not resp.model_id:
                resp.model_id = self.model_id
            return resp

        tool_names = {t.name for t in (tools or [])}
        already_called = {m.name for m in messages if m.role == "tool" and m.name}

        # 1) exercise skill discovery if a skill is advertised and tools allow it
        if "load_skill" in tool_names and "load_skill" not in already_called:
            skill_name = _first_skill_name(tools or [])
            return self._response(
                "",
                [ToolCall(id="call_load_skill", name="load_skill", arguments={"name": skill_name})],
                messages,
            )

        # 2) do a harmless read-only inspection
        if "list_dir" in tool_names and "list_dir" not in already_called:
            return self._response(
                "",
                [ToolCall(id="call_list_dir", name="list_dir", arguments={"path": "."})],
                messages,
            )

        # 3) finish
        return self._response(
            "Mock agent finished without modifying the repository.", [], messages
        )

    def _response(
        self, text: str, tool_calls: list[ToolCall], messages: list[Message]
    ) -> ModelResponse:
        prompt = "\n".join(m.content or "" for m in messages)
        usage = Usage(
            input_tokens=_approx_tokens(prompt),
            output_tokens=_approx_tokens(text) + 8 * len(tool_calls),
        )
        stop_reason = "tool_calls" if tool_calls else "stop"
        return ModelResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            model_id=self.model_id,
            stop_reason=stop_reason,
        )


def _first_skill_name(tools: list[ToolSpec]) -> str:
    for tool in tools:
        if tool.name != "load_skill":
            continue
        props = tool.parameters.get("properties", {})
        enum = props.get("name", {}).get("enum")
        if enum:
            return str(enum[0])
    return "unknown"
