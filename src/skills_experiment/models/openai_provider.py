"""OpenAI Chat Completions adapter.

Also covers anything OpenAI-compatible (Azure OpenAI, gateways, local servers)
by setting ``base_url`` in the model profile. The ``openai`` SDK is imported
lazily so the rest of the project works without it installed.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .base import ModelClient, ModelClientError
from .types import Message, ModelResponse, ToolCall, ToolSpec, Usage

# Parameters we forward verbatim from the model profile to the SDK call.
_PASSTHROUGH_PARAMS = ("temperature", "top_p", "max_tokens", "max_completion_tokens")


class OpenAIChatClient(ModelClient):
    provider = "openai"

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
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ModelClientError(
                "The 'openai' package is not installed. "
                "Install it with: pip install 'skills-experiment[openai]'"
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
        self._client = OpenAI(**client_kwargs)

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSpec]] = None,
    ) -> ModelResponse:
        self._ensure_client()
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [_to_openai_message(m) for m in messages],
        }
        for key in _PASSTHROUGH_PARAMS:
            if key in self.params and self.params[key] is not None:
                payload[key] = self.params[key]
        if tools:
            payload["tools"] = [_to_openai_tool(t) for t in tools]
            payload["tool_choice"] = "auto"

        try:
            raw = self._client.chat.completions.create(**payload)
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise ModelClientError(f"OpenAI request failed: {exc}") from exc

        return _from_openai_response(raw, self.model_id)

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
def _to_openai_message(m: Message) -> dict[str, Any]:
    if m.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": m.tool_call_id or "",
            "content": m.content or "",
        }
    if m.role == "assistant" and m.tool_calls:
        return {
            "role": "assistant",
            "content": m.content or None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in m.tool_calls
            ],
        }
    return {"role": m.role, "content": m.content or ""}


def _to_openai_tool(t: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        },
    }


def _from_openai_response(raw: Any, model_id: str) -> ModelResponse:
    choice = raw.choices[0]
    msg = choice.message
    tool_calls: list[ToolCall] = []
    for tc in getattr(msg, "tool_calls", None) or []:
        tool_calls.append(
            ToolCall.from_arguments_json(
                id=tc.id, name=tc.function.name, arguments_json=tc.function.arguments or ""
            )
        )
    usage_obj = getattr(raw, "usage", None)
    usage = Usage(
        input_tokens=getattr(usage_obj, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage_obj, "completion_tokens", 0) or 0,
        cache_read_tokens=_nested(usage_obj, "prompt_tokens_details", "cached_tokens"),
    )
    return ModelResponse(
        text=msg.content or "",
        tool_calls=tool_calls,
        usage=usage,
        model_id=getattr(raw, "model", model_id),
        stop_reason=choice.finish_reason,
        raw=raw,
    )


def _nested(obj: Any, *attrs: str) -> int:
    cur = obj
    for attr in attrs:
        cur = getattr(cur, attr, None)
        if cur is None:
            return 0
    return int(cur or 0)
