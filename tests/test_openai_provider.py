"""OpenAI-compatible payload tests that need no network or SDK install."""

from __future__ import annotations

from types import SimpleNamespace

from skills_experiment.models.openai_provider import OpenAIChatClient, _to_openai_message
from skills_experiment.models.types import Message


class _FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(
            content="answer",
            reasoning_content="because",
            tool_calls=None,
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=message, finish_reason="stop"),
            ],
            usage=SimpleNamespace(
                prompt_tokens=5,
                completion_tokens=7,
                prompt_tokens_details=SimpleNamespace(cached_tokens=2),
            ),
            model="deepseek-flash",
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def test_deepseek_thinking_payload_and_reasoning_roundtrip():
    fake = _FakeClient()
    client = OpenAIChatClient(
        model_id="deepseek-flash",
        params={
            "temperature": 0.2,
            "max_tokens": 16384,
            "thinking": "enabled",
            "reasoning_effort": "medium",
        },
    )
    client._client = fake

    response = client.complete([Message.user("hello")])
    kwargs = fake.chat.completions.kwargs

    assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}
    assert kwargs["reasoning_effort"] == "medium"
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 16384
    assert response.reasoning_content == "because"

    assistant = response.to_message()
    assert assistant.reasoning_content == "because"
    assert _to_openai_message(assistant)["reasoning_content"] == "because"
