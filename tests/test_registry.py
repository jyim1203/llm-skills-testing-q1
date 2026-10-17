"""Model registry + provider-swap tests."""

from __future__ import annotations

import pytest

from skills_experiment.models.base import ModelClientError
from skills_experiment.models.mock import MockModelClient
from skills_experiment.models.registry import get_registry


def test_registry_contains_expected_profiles():
    registry = get_registry()
    names = set(registry.names())
    assert {"deepseek-flash", "claude-opus", "gemini-pro", "mock"} <= names


@pytest.mark.parametrize(
    "profile,provider",
    [
        ("deepseek-flash", "openai"),
        ("claude-opus", "anthropic"),
        ("gemini-pro", "google"),
        ("mock", "mock"),
    ],
)
def test_profiles_map_to_providers(profile, provider):
    assert get_registry().get(profile).provider == provider


def test_swap_models_is_config_only():
    """Each named profile creates the client for its own provider."""
    registry = get_registry()
    assert registry.get("deepseek-flash").provider == "openai"
    assert registry.get("claude-opus").provider == "anthropic"
    # mock needs no credentials, so it is safe to instantiate in tests
    client = registry.create("mock")
    assert isinstance(client, MockModelClient)


def test_unknown_model_raises():
    with pytest.raises(ModelClientError):
        get_registry().get("does-not-exist")


def test_api_key_required_is_reported_clearly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile = get_registry().get("claude-opus")
    # An empty key must raise a helpful error rather than a bare provider error.
    with pytest.raises(ModelClientError):
        profile.resolve_api_key()
