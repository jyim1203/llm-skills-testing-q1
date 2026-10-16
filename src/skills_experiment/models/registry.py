"""TOML-driven model registry.

This is the seam that makes models swappable. Adding or changing a model is a
matter of editing a file in ``configs/models/`` -- no Python changes required.

    from skills_experiment.models import get_registry
    client = get_registry().create("gpt-6-luna")   # or "claude-opus", "gemini-pro"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .. import paths
from ..config import load_toml
from ..env import load_dotenv
from .base import ModelClient, ModelClientError

# Provider key -> factory(profile) -> ModelClient. Factories are defined at the
# bottom of this module and import their provider SDK lazily, so importing the
# registry never requires any provider package to be installed.
_PROVIDER_ALIASES: dict[str, str] = {
    "openai": "openai",
    "chatgpt": "openai",
    "azure": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "google": "google",
    "gemini": "google",
    "mock": "mock",
    "echo": "mock",
}

_DEFAULT_API_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
}


@dataclass
class ModelProfile:
    """A named, configured model. Mirrors a file in ``configs/models/``."""

    name: str
    provider: str
    model_id: str
    params: dict[str, Any] = field(default_factory=dict)
    pricing: dict[str, float] = field(default_factory=dict)
    api_key_env: str = ""
    base_url: str = ""
    notes: str = ""
    source_path: Optional[Path] = None

    @classmethod
    def from_file(cls, path: str | Path) -> "ModelProfile":
        data = load_toml(path)
        provider = _PROVIDER_ALIASES.get(
            str(data.get("provider", "")).lower(), str(data.get("provider", "")).lower()
        )
        return cls(
            name=data.get("name", Path(path).stem),
            provider=provider,
            model_id=data.get("model_id", ""),
            params=dict(data.get("params", {})),
            pricing=dict(data.get("pricing", {})),
            api_key_env=data.get("api_key_env", "") or "",
            base_url=data.get("base_url", "") or "",
            notes=data.get("notes", "") or "",
            source_path=Path(path),
        )

    # -- client construction ------------------------------------------------ #
    def resolve_api_key(self) -> Optional[str]:
        """Return the API key for this profile, or ``None`` if none is needed.

        Raises if the profile needs a key but the environment does not provide
        one -- callers get a clear, early error instead of an opaque SDK error.
        """
        if self.provider == "mock":
            return None
        env_name = self.api_key_env or _DEFAULT_API_KEY_ENV.get(self.provider, "")
        if not env_name:
            return None
        load_dotenv()
        key = _getenv(env_name)
        if not key:
            raise ModelClientError(
                f"Model profile '{self.name}' (provider '{self.provider}') requires "
                f"an API key in environment variable {env_name}. "
                f"Copy .env.example to .env and set it, or export it in your shell."
            )
        return key

    def create_client(self) -> ModelClient:
        factory = _FACTORY_REGISTRY.get(self.provider)
        if factory is None:
            raise ModelClientError(
                f"Unknown provider '{self.provider}' for model '{self.name}'. "
                f"Known providers: {sorted(_FACTORY_REGISTRY)}"
            )
        return factory(self)

    def summary(self) -> str:
        return f"{self.name:<16} provider={self.provider:<10} model_id={self.model_id}"


def _getenv(name: str) -> str:
    import os

    return os.environ.get(name, "").strip()


class ModelRegistry:
    """Loads every ``*.toml`` model profile in a directory."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory else paths.MODELS_DIR
        self._profiles: dict[str, ModelProfile] = {}
        self.reload()

    def reload(self) -> None:
        self._profiles.clear()
        if not self.directory.exists():
            return
        for path in sorted(self.directory.glob("*.toml")):
            profile = ModelProfile.from_file(path)
            self._profiles[profile.name] = profile

    # -- access ------------------------------------------------------------- #
    def names(self) -> list[str]:
        return sorted(self._profiles)

    def profiles(self) -> list[ModelProfile]:
        return [self._profiles[n] for n in self.names()]

    def get(self, name: str) -> ModelProfile:
        try:
            return self._profiles[name]
        except KeyError:
            raise ModelClientError(
                f"No model profile named '{name}'. Available: {self.names()}"
            ) from None

    def create(self, name: str) -> ModelClient:
        return self.get(name).create_client()


_DEFAULT_REGISTRY: ModelRegistry | None = None


def get_registry(directory: Path | None = None) -> ModelRegistry:
    """Return the default registry (cached), or one rooted at ``directory``."""
    global _DEFAULT_REGISTRY
    if directory is not None:
        return ModelRegistry(directory)
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = ModelRegistry()
    return _DEFAULT_REGISTRY


# --------------------------------------------------------------------------- #
# Provider factories. Each imports its SDK lazily inside the factory.
# --------------------------------------------------------------------------- #
def _make_mock(profile: ModelProfile) -> ModelClient:
    from .mock import MockModelClient

    return MockModelClient(
        model_id=profile.model_id, params=profile.params, pricing=profile.pricing
    )


def _make_openai(profile: ModelProfile) -> ModelClient:
    from .openai_provider import OpenAIChatClient

    return OpenAIChatClient(
        model_id=profile.model_id,
        api_key=profile.resolve_api_key(),
        base_url=profile.base_url,
        params=profile.params,
        pricing=profile.pricing,
    )


def _make_anthropic(profile: ModelProfile) -> ModelClient:
    from .anthropic_provider import AnthropicChatClient

    return AnthropicChatClient(
        model_id=profile.model_id,
        api_key=profile.resolve_api_key(),
        base_url=profile.base_url,
        params=profile.params,
        pricing=profile.pricing,
    )


def _make_google(profile: ModelProfile) -> ModelClient:
    from .gemini_provider import GeminiChatClient

    return GeminiChatClient(
        model_id=profile.model_id,
        api_key=profile.resolve_api_key(),
        base_url=profile.base_url,
        params=profile.params,
        pricing=profile.pricing,
    )


_FACTORY_REGISTRY: dict[str, Callable[[ModelProfile], ModelClient]] = {
    "mock": _make_mock,
    "openai": _make_openai,
    "anthropic": _make_anthropic,
    "google": _make_google,
}
