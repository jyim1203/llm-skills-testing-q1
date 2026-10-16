"""Provider-agnostic model layer.

Public surface:

* :class:`ModelClient` -- the interface every provider implements.
* :func:`get_registry` / :class:`ModelRegistry` -- TOML-driven selection.
* normalized types (:class:`Message`, :class:`ToolCall`, :class:`ModelResponse`).
"""

from __future__ import annotations

from .base import ModelClient, ModelClientError
from .registry import ModelProfile, ModelRegistry, get_registry
from .types import Message, ModelResponse, ToolCall, ToolSpec, Usage

__all__ = [
    "ModelClient",
    "ModelClientError",
    "ModelProfile",
    "ModelRegistry",
    "get_registry",
    "Message",
    "ModelResponse",
    "ToolCall",
    "ToolSpec",
    "Usage",
]
