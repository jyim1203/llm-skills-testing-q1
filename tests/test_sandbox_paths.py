"""Sandbox path + patch-capture regression tests.

The Docker sandbox runs on a host (possibly Windows) but executes inside a Linux
container, so container paths must always be POSIX. Before the fix, ``Path`` on
Windows turned ``/testbed/x`` into ``\\testbed\\x`` and every read/write/list
silently targeted the wrong location.
"""

from __future__ import annotations

from pathlib import Path

from skills_experiment.sandbox.docker import DockerSandbox
from skills_experiment.sandbox.noop import NoopSandbox


def _sandbox(tmp_path: Path) -> DockerSandbox:
    # Constructing the sandbox does not touch Docker (only prepare() does).
    return DockerSandbox(tmp_path / "work")


def test_container_path_is_posix_for_relative(tmp_path):
    sandbox = _sandbox(tmp_path)
    assert sandbox._container_path("astroid/nodes/as_string.py") == (
        "/testbed/astroid/nodes/as_string.py"
    )


def test_container_path_preserves_absolute(tmp_path):
    sandbox = _sandbox(tmp_path)
    assert sandbox._container_path("/testbed/astroid/x.py") == "/testbed/astroid/x.py"
    assert sandbox._container_path("/tmp/scratch") == "/tmp/scratch"


def test_container_path_never_uses_backslashes(tmp_path):
    sandbox = _sandbox(tmp_path)
    for raw in ["pkg/module.py", "/testbed/pkg/module.py", "./a/b"]:
        assert "\\" not in sandbox._container_path(raw)


def test_noop_diff_reflects_writes(tmp_path):
    sandbox = NoopSandbox(tmp_path / "work")
    assert sandbox.diff().strip() == ""
    sandbox.write_file("pkg/module.py", "def add(a, b):\n    return a + b + 1\n")
    diff = sandbox.diff()
    assert "pkg/module.py" in diff
    assert "+    return a + b + 1" in diff
