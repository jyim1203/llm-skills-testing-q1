"""Anthropic Messages API adapter (Claude).

The ``anthropic`` SDK is imported lazily. Anthropic's API differs from OpenAI's
in two ways the translation layer handles explicitly:

* the system prompt is a separate top-level argument, not a message; and
* tool results are ``tool_result`` content blocks inside a *user* message, so
  consecutive tool results are merged into a single user turn.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import ModelClient, ModelClientError
from .types import Message, ModelResponse, ToolCall, ToolSpec, Usage

_PASSTHROUGH_PARAMS = ("temperature", "top_p", "top_k", "stop_sequences")


class AnthropicChatClient(ModelClient):
    provider = "anthropic"

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: str = "",
        params: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_id=model_id, params=params, **kwargs)
        self._api_key = api_key
        self._base_url = base_url or ""
        self._client: Any = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ModelClientError(
                "The 'anthropic' package is not installed. "
                "Install it with: pip install 'skills-experiment[anthropic]'"
            ) from exc
        client_kwargs: dict[str, Any] = {}
        if self._api_key:
            client_kwargs["api_key"] = self._api_key
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        timeout = self.params.get("timeout")
        if timeout:
            client_kwargs["timeout"] = timeout
        max_retries = self.params.get("max_retries")
        if max_retries is not None:
            client_kwargs["max_retries"] = int(max_retries)
        self._client = anthropic.Anthropic(**client_kwargs)

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSpec]] = None,
    ) -> ModelResponse:
        self._ensure_client()
        system, converted = _to_anthropic_messages(messages)

        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": converted,
            "max_tokens": int(self.params.get("max_tokens", 8192)),
        }
        if system:
            payload["system"] = system
        for key in _PASSTHROUGH_PARAMS:
            if key in self.params and self.params[key] is not None:
                payload[key] = self.params[key]
        if tools:
            payload["tools"] = [_to_anthropic_tool(t) for t in tools]

        try:
            raw = self._client.messages.create(**payload)
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise ModelClientError(f"Anthropic request failed: {exc}") from exc

        return _from_anthropic_response(raw, self.model_id)

    def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass


# --------------------------------------------------------------------------- #
# Translation helpers
# --------------------------------------------------------------------------- #
def _to_anthropic_messages(
    messages: list[Message],
) -> tuple[str, list[dict[str, Any]]]:
    system_parts = [m.content for m in messages if m.role == "system" and m.content]
    system = "\n\n".join(system_parts)

    converted: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            continue
        if m.role == "user":
            blocks: list[dict[str, Any]] = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            _append_merged(converted, "user", blocks)
        elif m.role == "tool":
            _append_merged(
                converted,
                "user",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id or "",
                        "content": m.content or "",
                    }
                ],
            )
        elif m.role == "assistant":
            blocks = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                blocks.append(
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                )
            if not blocks:
                blocks = [{"type": "text", "text": ""}]
            _append_merged(converted, "assistant", blocks)

    return system, converted


def _append_merged(
    converted: list[dict[str, Any]], role: str, blocks: list[dict[str, Any]]
) -> None:
    if not blocks:
        return
    if converted and converted[-1]["role"] == role:
        converted[-1]["content"].extend(blocks)
    else:
        converted.append({"role": role, "content": list(blocks)})


def _to_anthropic_tool(t: ToolSpec) -> dict[str, Any]:
    return {
        "name": t.name,
        "description": t.description,
        "input_schema": t.parameters,
    }


def _from_anthropic_response(raw: Any, model_id: str) -> ModelResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in getattr(raw, "content", None) or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(getattr(block, "text", "") or "")
        elif block_type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=dict(getattr(block, "input", {}) or {}),
                )
            )
    usage_obj = getattr(raw, "usage", None)
    usage = Usage(
        input_tokens=getattr(usage_obj, "input_tokens", 0) or 0,
        output_tokens=getattr(usage_obj, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(usage_obj, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(usage_obj, "cache_creation_input_tokens", 0) or 0,
    )
    return ModelResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        usage=usage,
        model_id=getattr(raw, "model", model_id),
        stop_reason=getattr(raw, "stop_reason", None),
        raw=raw,
    )
