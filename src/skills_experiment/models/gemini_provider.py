"""Google Gemini adapter (``google-genai`` SDK).

The SDK is imported lazily. Gemini's content model differs from the chat-style
APIs: turns are ``Content`` objects with ``parts``, roles are ``user`` / ``model``,
and tool results are ``function_response`` parts.

Best-effort: this adapter is written against the public ``google-genai``
interface but has not been executed against a live endpoint in this checkout.
Validate it with a single live smoke call before trusting it for results.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import ModelClient, ModelClientError
from .types import Message, ModelResponse, ToolCall, ToolSpec, Usage

_PASSTHROUGH_PARAMS = ("temperature", "top_p")


class GeminiChatClient(ModelClient):
    provider = "google"

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: str = "",
        params: Optional[dict[str, Any]] = None,
        pricing: Optional[dict[str, float]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_id=model_id, params=params, pricing=pricing, **kwargs)
        self._api_key = api_key
        self._base_url = base_url or ""
        self._client: Any = None
        self._types: Any = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ModelClientError(
                "The 'google-genai' package is not installed. "
                "Install it with: pip install 'skills-experiment[google]'"
            ) from exc
        self._types = types
        client_kwargs: dict[str, Any] = {}
        if self._api_key:
            client_kwargs["api_key"] = self._api_key
        if self._base_url:
            client_kwargs["http_options"] = types.HttpOptions(base_url=self._base_url)
        self._client = genai.Client(**client_kwargs)

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSpec]] = None,
    ) -> ModelResponse:
        self._ensure_client()
        types = self._types

        system_parts = [m.content for m in messages if m.role == "system" and m.content]
        system_instruction = "\n\n".join(system_parts) or None
        contents = _to_gemini_contents(types, messages)

        config_kwargs: dict[str, Any] = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if "max_tokens" in self.params:
            config_kwargs["max_output_tokens"] = int(self.params["max_tokens"])
        for key in _PASSTHROUGH_PARAMS:
            if key in self.params and self.params[key] is not None:
                config_kwargs[key] = self.params[key]
        if tools:
            config_kwargs["tools"] = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters=t.parameters,
                        )
                        for t in tools
                    ]
                )
            ]
        config = types.GenerateContentConfig(**config_kwargs)

        try:
            raw = self._client.models.generate_content(
                model=self.model_id, contents=contents, config=config
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise ModelClientError(f"Gemini request failed: {exc}") from exc

        return _from_gemini_response(raw, self.model_id)


# --------------------------------------------------------------------------- #
# Translation helpers
# --------------------------------------------------------------------------- #
def _to_gemini_contents(types: Any, messages: list[Message]) -> list[Any]:
    contents: list[Any] = []
    for m in messages:
        if m.role == "system":
            continue
        if m.role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=m.content or "")]))
        elif m.role == "assistant":
            parts: list[Any] = []
            if m.content:
                parts.append(types.Part(text=m.content))
            for tc in m.tool_calls:
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(name=tc.name, args=tc.arguments)
                    )
                )
            if parts:
                contents.append(types.Content(role="model", parts=parts))
        elif m.role == "tool":
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=m.name or "",
                                response={"result": m.content or ""},
                            )
                        )
                    ],
                )
            )
    return contents


def _from_gemini_response(raw: Any, model_id: str) -> ModelResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    candidates = getattr(raw, "candidates", None) or []
    if candidates:
        content = getattr(candidates[0], "content", None)
        for part in getattr(content, "parts", None) or []:
            text = getattr(part, "text", None)
            if text:
                text_parts.append(text)
            fc = getattr(part, "function_call", None)
            if fc is not None:
                args = getattr(fc, "args", {}) or {}
                tool_calls.append(
                    ToolCall(
                        id=f"call_{len(tool_calls)}",
                        name=getattr(fc, "name", ""),
                        arguments=dict(args),
                    )
                )
    usage_obj = getattr(raw, "usage_metadata", None)
    usage = Usage(
        input_tokens=getattr(usage_obj, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage_obj, "candidates_token_count", 0) or 0,
        cache_read_tokens=getattr(usage_obj, "cached_content_token_count", 0) or 0,
    )
    return ModelResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        usage=usage,
        model_id=model_id,
        stop_reason=None,
        raw=raw,
    )
