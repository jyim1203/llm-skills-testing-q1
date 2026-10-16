"""Local (host) sandbox.

Runs commands and edits files directly on the host inside a per-attempt
workspace. This is convenient for smoke tests and read-only inspection, but it
does **not** reproduce a benchmark's declared environment and should not be used
for reported SWE-bench results. Use the Docker sandbox for those.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .base import CommandResult, Sandbox, SandboxError

if TYPE_CHECKING:
    from ..benchmark.swebench_lite import TaskInstance


class LocalSandbox(Sandbox):
    """Execute commands on the host with ``cwd`` set to the workspace."""

    def __init__(
        self,
        workdir: Path,
        repo_url_template: str = "https://github.com/{repo}.git",
        env: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(workdir)
        self.repo_url_template = repo_url_template
        self.env = env or {}

    def prepare(self, task: "TaskInstance") -> None:
        """Clone ``task.repo`` and check out ``task.base_commit``."""
        if (self.workdir / ".git").exists():
            self.base_ref = task.base_commit or self.base_ref
            return  # already prepared (idempotent)
        if any(self.workdir.iterdir()):
            raise SandboxError(
                f"Workspace {self.workdir} is not empty; refusing to clone over it."
            )
        url = self.repo_url_template.format(repo=task.repo)
        steps = [
            ["git", "init", "-q"],
            ["git", "remote", "add", "origin", url],
            ["git", "fetch", "--quiet", "--filter=blob:none", "origin"],
            ["git", "checkout", "-q", task.base_commit],
        ]
        for cmd in steps:
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=1800,
            )
            if result.returncode != 0:
                # Retry the fetch once without the partial-clone filter.
                if cmd[:2] == ["git", "fetch"]:
                    retry = subprocess.run(
                        ["git", "fetch", "--quiet", "origin"],
                        cwd=self.workdir,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=1800,
                    )
                    if retry.returncode == 0:
                        continue
                raise SandboxError(
                    f"git step failed: {' '.join(cmd)}\n{result.stderr.strip()}"
                )
        self.base_ref = task.base_commit

    def run(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        import os

        env = dict(os.environ)
        env.update(self.env)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(command=command, exit_code=124, timed_out=True)
        except OSError as exc:
            return CommandResult(command=command, exit_code=127, stderr=str(exc))
        return CommandResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )

    @staticmethod
    def available() -> bool:
        return shutil.which("git") is not None
