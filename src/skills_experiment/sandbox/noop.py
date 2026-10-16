"""Offline, in-memory sandbox.

Nothing touches the host filesystem or spawns processes. Used by the mock smoke
test and unit tests so the pipeline can be validated with zero risk and zero
dependencies. ``diff()`` renders a real unified diff of the synthetic files so
the patch-capture path is still exercised.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .base import CommandResult, Sandbox

if TYPE_CHECKING:
    from ..benchmark.swebench_lite import TaskInstance

_SEED_FILES: dict[str, str] = {
    "README.md": "# scratch repository\n\nUsed by the offline smoke test.\n",
    "pkg/__init__.py": "",
    "pkg/module.py": "def add(a, b):\n    return a + b\n",
}


class NoopSandbox(Sandbox):
    """An in-memory workspace; commands are recorded but never executed."""

    def __init__(self, workdir: Path) -> None:
        super().__init__(workdir)
        self.files: dict[str, str] = dict(_SEED_FILES)
        self.original: dict[str, str] = dict(_SEED_FILES)
        self.commands: list[str] = []

    def prepare(self, task: "TaskInstance") -> None:
        return None

    def run(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        self.commands.append(command)
        return CommandResult(
            command=command,
            exit_code=0,
            stdout=f"[dry-run] command not executed: {command}",
        )

    def _resolve(self, path: str) -> Path:  # pragma: no cover - not used for I/O
        return Path(path)

    def read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        if path not in self.files:
            return f"[error] file not found: {path}"
        lines = self.files[path].splitlines()
        lo = start_line or 1
        hi = end_line or len(lines)
        return "\n".join(f"{i + lo:>4}: {line}" for i, line in enumerate(lines[lo - 1 : hi]))

    def write_file(self, path: str, content: str) -> str:
        self.files[path] = content
        return f"[ok] wrote {len(content)} bytes to {path}"

    def list_dir(self, path: str = ".") -> str:
        names = set()
        for f in self.files:
            parts = f.split("/")
            if path in (".", "", "/"):
                names.add(parts[0] + ("/" if len(parts) > 1 else ""))
            elif f.startswith(path.strip("/") + "/"):
                names.add(parts[len(path.strip("/").split("/"))] + "/")
        return "\n".join(sorted(names)) if names else "(empty)"

    def diff(self) -> str:
        chunks: list[str] = []
        for path in sorted(set(self.original) | set(self.files)):
            before = self.original.get(path, "")
            after = self.files.get(path, "")
            if before == after:
                continue
            diff = difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
            chunks.append("".join(diff))
        return "".join(chunks)
