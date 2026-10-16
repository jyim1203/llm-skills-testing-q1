"""Abstract model client interface.

All provider adapters implement :class:`ModelClient`. The rest of the codebase
depends only on this interface, so a new provider (or a self-hosted endpoint)
can be added without touching the agent loop or the experimental conditions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .types import Message, ModelResponse, ToolSpec


class ModelClientError(RuntimeError):
    """Raised when a provider call fails in a way callers should know about."""


class ModelClient(ABC):
    """A chat-completion client with optional tool calling.

    Attributes
    ----------
    provider:
        Short provider key, e.g. ``"openai"``, ``"anthropic"``, ``"google"``.
    model_id:
        The exact model identifier sent to the provider (recorded in run logs).
    """

    provider: str = "unknown"

    def __init__(
        self,
        model_id: str,
        params: Optional[dict[str, Any]] = None,
        pricing: Optional[dict[str, float]] = None,
        **kwargs: Any,
    ) -> None:
        self.model_id = model_id
        self.params: dict[str, Any] = dict(params or {})
        self.pricing: dict[str, float] = dict(pricing or {})
        self.extra: dict[str, Any] = dict(kwargs)

    # -- required ----------------------------------------------------------- #
    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSpec]] = None,
    ) -> ModelResponse:
        """Produce one assistant turn for ``messages``."""

    # -- optional ----------------------------------------------------------- #
    def close(self) -> None:
        """Release any held resources. Safe to call multiple times."""

    def __enter__(self) -> "ModelClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- helpers ------------------------------------------------------------ #
    def estimate_cost(self, usage_tokens: int, *, output: bool = False) -> float:
        """Estimate USD cost for a token count using the profile's pricing.

        Pricing values are USD per 1,000,000 tokens.
        """
        rate = self.pricing.get("output" if output else "input", 0.0)
        return usage_tokens / 1_000_000 * rate

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<{type(self).__name__} provider={self.provider} model_id={self.model_id!r}>"
