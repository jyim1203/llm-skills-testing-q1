"""Sandbox abstraction: where an agent's commands and file edits take place.

Isolation is a first-class requirement of this study (see handoff sections 8 and
10). Every attempt gets its *own* sandbox rooted at its own workspace directory,
so no file, git state, or process can leak from one condition/attempt into
another.

Two implementations are provided:

* :class:`~skills_experiment.sandbox.local.LocalSandbox` -- runs commands
  directly on the host. Fast; suitable for smoke tests and read-only checks.
* :class:`~skills_experiment.sandbox.docker.DockerSandbox` -- runs commands in
  the per-instance SWE-bench image. This is what a trustworthy evaluation needs.

``NoopSandbox`` is a third, offline implementation used by the mock smoke test.
"""

from __future__ import annotations

import subprocess  # noqa: F401  (re-exported for sandboxes)
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # avoid a runtime import cycle
    from ..benchmark.swebench_lite import TaskInstance

# Keep tool output bounded so a runaway command cannot blow up the context.
MAX_OUTPUT_CHARS = 20_000


class SandboxError(RuntimeError):
    """Raised for sandbox setup/execution failures that callers should see."""


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def combined(self, max_chars: int = MAX_OUTPUT_CHARS) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append("[stderr]\n" + self.stderr)
        if self.timed_out:
            parts.append("[timed out]")
        text = "\n".join(parts) if parts else f"(no output; exit code {self.exit_code})"
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [truncated {len(text) - max_chars} chars]"
        return text


class Sandbox(ABC):
    """A filesystem + shell environment scoped to one workspace directory."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = Path(workdir).resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        # The commit the repo is checked out at, captured at prepare() time so a
        # candidate patch is correct even if the agent commits its changes.
        self.base_ref: Optional[str] = None

    # -- lifecycle ---------------------------------------------------------- #
    def prepare(self, task: "TaskInstance") -> None:
        """Set up the repository at the correct base commit. Default: no-op."""
        return None

    def cleanup(self) -> None:
        """Release resources held by the sandbox. Default: no-op."""
        return None

    # -- execution ---------------------------------------------------------- #
    @abstractmethod
    def run(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """Execute a shell command in the workspace."""

    # -- filesystem (shared, path-checked implementation) ------------------- #
    def _resolve(self, path: str) -> Path:
        candidate = (self.workdir / path).resolve()
        if candidate != self.workdir and self.workdir not in candidate.parents:
            raise SandboxError(f"Refusing to access path outside workspace: {path!r}")
        return candidate

    def read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        target = self._resolve(path)
        if not target.exists():
            return f"[error] file not found: {path}"
        if target.is_dir():
            return f"[error] not a file: {path}"
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            return f"[error] could not read {path}: {exc}"
        lo = (start_line or 1)
        hi = (end_line or len(lines))
        selected = lines[lo - 1 : hi]
        width = len(str(hi))
        return "\n".join(f"{i + lo:>{width}}: {line}" for i, line in enumerate(selected))

    def write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return f"[error] could not write {path}: {exc}"
        return f"[ok] wrote {len(content)} bytes to {path}"

    def list_dir(self, path: str = ".") -> str:
        target = self._resolve(path)
        if not target.exists():
            return f"[error] directory not found: {path}"
        if not target.is_dir():
            return f"[error] not a directory: {path}"
        entries = sorted(
            (f"{e.name}/" if e.is_dir() else e.name) for e in target.iterdir()
        )
        return "\n".join(entries) if entries else "(empty)"

    # -- diff --------------------------------------------------------------- #
    def diff(self) -> str:
        """Return the candidate patch: the working tree vs the base commit.

        ``git add -A`` stages new files (so they appear in the diff), and the
        diff is taken against ``base_ref`` rather than ``HEAD`` so an agent that
        commits its work still produces the full patch.
        """
        ref = self.base_ref or "HEAD"
        result = self.run(f"git add -A && git diff --cached --no-color {ref}", timeout=120)
        return result.stdout

    # -- introspection ------------------------------------------------------ #
    def backend(self) -> str:
        return type(self).__name__
