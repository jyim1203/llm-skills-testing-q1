"""Provider-agnostic chat types.

Every provider adapter translates to and from these types. The agent loop and
the experimental conditions only ever see this normalized representation, which
is what makes swapping models (OpenAI / Anthropic / Google) a configuration
change rather than a code change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    """A model's request to invoke a tool."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_arguments_json(cls, id: str, name: str, arguments_json: str) -> "ToolCall":
        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError:
            # Keep the raw payload so the loop can report a clean tool error
            # rather than crashing the run.
            args = {"__raw__": arguments_json}
        if not isinstance(args, dict):
            args = {"__raw__": arguments_json}
        return cls(id=id, name=name, arguments=args)


@dataclass
class Message:
    """One normalized chat message."""

    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    # -- convenience constructors ------------------------------------------- #
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)

    @classmethod
    def assistant(
        cls, content: str = "", tool_calls: Optional[list[ToolCall]] = None
    ) -> "Message":
        return cls(role="assistant", content=content, tool_calls=tool_calls or [])

    @classmethod
    def tool_result(cls, tool_call_id: str, content: str, name: Optional[str] = None) -> "Message":
        return cls(role="tool", content=content, tool_call_id=tool_call_id, name=name)


@dataclass
class ToolSpec:
    """A tool the model may call, in JSON-Schema form."""

    name: str
    description: str
    parameters: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )


@dataclass
class Usage:
    """Token accounting for a single request or an accumulated run."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )

    def __iadd__(self, other: "Usage") -> "Usage":
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens
        return self

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ModelResponse:
    """A normalized model completion."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model_id: str = ""
    stop_reason: Optional[str] = None
    raw: Any = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)

    def to_message(self) -> Message:
        return Message.assistant(self.text, self.tool_calls)
