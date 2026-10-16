"""Docker sandbox.

Runs commands inside the per-instance SWE-bench evaluation image, which is the
only way to get trustworthy results: the image pins the OS, Python version, and
project dependencies that the grader also uses.

Validated end to end against a real SWE-bench dev image with
``scripts/validate_sandbox.py`` (container start, exec, read/write/list, and
patch capture). Re-run that script on a dev instance after changing this file.

Design notes
------------
* The image name comes from the dataset's ``image`` field on the task.
* A long-lived container is started per attempt and removed on cleanup, so
  attempts cannot share state.
* File operations are proxied through ``docker exec`` rather than touching the
  host, keeping the agent strictly inside the container.
* Container paths are POSIX (``PurePosixPath``); never use the host's ``Path``
  flavour here, or Windows would render ``/testbed/x`` as ``\\testbed\\x``.
* Subprocess output is decoded as UTF-8 with ``errors="replace"``; the Windows
  locale codec (cp1252) cannot decode arbitrary container output and would drop
  results with a ``UnicodeDecodeError``.
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Optional

from .base import CommandResult, Sandbox, SandboxError

if TYPE_CHECKING:
    from ..benchmark.swebench_lite import TaskInstance

CONTAINER_WORKDIR = "/testbed"


class DockerSandbox(Sandbox):
    def __init__(
        self,
        workdir: Path,
        image: str = "",
        image_template: str = "swebench/sweb.eval.x86_64.{repo_slug}:latest",
        container_workdir: str = CONTAINER_WORKDIR,
    ) -> None:
        super().__init__(workdir)
        self.image = image
        self.image_template = image_template
        self.container_workdir = container_workdir
        self.container_name = f"skills-exp-{uuid.uuid4().hex[:12]}"
        self._started = False

    # -- availability ------------------------------------------------------- #
    @staticmethod
    def available() -> bool:
        return shutil.which("docker") is not None

    @staticmethod
    def _require_docker() -> None:
        if not shutil.which("docker"):
            raise SandboxError(
                "Docker was not found on PATH. The Docker sandbox is required for "
                "trustworthy SWE-bench evaluation. Install Docker Desktop (or the "
                "docker engine) and ensure 'docker' is runnable."
            )

    def _image_for(self, task: "TaskInstance") -> str:
        if task.image:
            return task.image
        if self.image:
            return self.image
        slug = task.repo.replace("/", "_")
        return self.image_template.format(repo_slug=slug, repo=task.repo)

    # -- lifecycle ---------------------------------------------------------- #
    def prepare(self, task: "TaskInstance") -> None:
        self._require_docker()
        image = self._image_for(task)
        self.image = image
        self._run_host(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.container_name,
                "-w",
                self.container_workdir,
                image,
                "tail",
                "-f",
                "/dev/null",
            ]
        )
        self._started = True
        base = self.run("git rev-parse HEAD")
        self.base_ref = base.stdout.strip() or None

    def cleanup(self) -> None:
        if self._started:
            try:
                self._run_host(["docker", "rm", "-f", self.container_name])
            except SandboxError:
                pass
            finally:
                self._started = False

    # -- execution ---------------------------------------------------------- #
    def run(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        self._require_docker()
        try:
            proc = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-w",
                    self.container_workdir,
                    self.container_name,
                    "bash",
                    "-lc",
                    command,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(command=command, exit_code=124, timed_out=True)
        return CommandResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )

    # -- filesystem via docker exec ----------------------------------------- #
    def _container_path(self, path: str) -> str:
        # Container paths are POSIX; never use the host's path flavour here
        # (on Windows `Path` would render "/testbed/x" as "\\testbed\\x").
        p = PurePosixPath(path)
        if p.is_absolute():
            return str(p)
        return str(PurePosixPath(self.container_workdir) / p)

    def read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        cpath = self._container_path(path)
        result = self.run(f"cat {cpath!r}")
        if result.exit_code != 0:
            return f"[error] could not read {path}: {result.stderr.strip()}"
        lines = result.stdout.splitlines()
        lo = start_line or 1
        hi = end_line or len(lines)
        return "\n".join(f"{i + lo:>4}: {line}" for i, line in enumerate(lines[lo - 1 : hi]))

    def write_file(self, path: str, content: str) -> str:
        cpath = self._container_path(path)
        payload = content
        result = self.run(
            f"mkdir -p \"$(dirname {cpath!r})\" && cat > {cpath!r} <<'SKILLSEXP_EOF'\n"
            f"{payload}\nSKILLSEXP_EOF"
        )
        if result.exit_code != 0:
            return f"[error] could not write {path}: {result.stderr.strip()}"
        return f"[ok] wrote {len(content)} bytes to {path}"

    def list_dir(self, path: str = ".") -> str:
        cpath = self._container_path(path)
        result = self.run(f"ls -1 {cpath!r}")
        if result.exit_code != 0:
            return f"[error] could not list {path}: {result.stderr.strip()}"
        return result.stdout.strip() or "(empty)"

    # -- provenance --------------------------------------------------------- #
    def provenance(self) -> dict[str, str]:
        """The exact image tag plus its immutable digest, for the run log."""
        info: dict[str, str] = {"docker_image": self.image}
        try:
            proc = self._run_host(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{if .RepoDigests}}{{index .RepoDigests 0}}{{end}}",
                    self.container_name,
                ]
            )
        except SandboxError:
            return info
        digest = proc.stdout.strip()
        if digest:
            info["docker_image_digest"] = digest
        return info

    # -- host-side docker calls --------------------------------------------- #
    def _run_host(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
        if proc.returncode != 0:
            raise SandboxError(f"{' '.join(cmd)} failed:\n{proc.stderr.strip()}")
        return proc


# --------------------------------------------------------------------------- #
# Image helpers (used by the `preflight` command for reproducibility)
# --------------------------------------------------------------------------- #
def image_digest(image: str) -> str:
    """Return the immutable registry digest of a local image, or ``""``."""
    try:
        proc = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{if .RepoDigests}}{{index .RepoDigests 0}}{{end}}",
                image,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except Exception:  # noqa: BLE001 - best-effort
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def pull_image(image: str, timeout: int = 1800) -> None:
    """Pull ``image`` from its registry (idempotent)."""
    proc = subprocess.run(
        ["docker", "pull", image],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise SandboxError(f"docker pull {image} failed:\n{proc.stderr.strip()}")
