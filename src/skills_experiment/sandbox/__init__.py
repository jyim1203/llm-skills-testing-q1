"""Sandbox implementations."""

from __future__ import annotations

from pathlib import Path

from .base import CommandResult, Sandbox, SandboxError
from .docker import DockerSandbox
from .local import LocalSandbox
from .noop import NoopSandbox

_BACKENDS = {
    "local": LocalSandbox,
    "docker": DockerSandbox,
    "noop": NoopSandbox,
}


def make_sandbox(kind: str, workdir: Path, **kwargs) -> Sandbox:
    """Factory for sandbox backends by name."""
    try:
        backend = _BACKENDS[kind]
    except KeyError:
        raise SandboxError(
            f"Unknown sandbox kind {kind!r}. Known kinds: {sorted(_BACKENDS)}"
        ) from None
    return backend(workdir, **kwargs)


__all__ = [
    "CommandResult",
    "Sandbox",
    "SandboxError",
    "DockerSandbox",
    "LocalSandbox",
    "NoopSandbox",
    "make_sandbox",
]
