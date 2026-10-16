#!/usr/bin/env python
"""Validate the Docker sandbox against a real SWE-bench dev image.

    python scripts/validate_sandbox.py pylint-dev__astroid-1268

Exercises the agent-side runtime end to end inside the per-instance image:
container start, command execution, file read/write/list, and patch capture.
Dev instances only. Requires Docker to be running.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment import paths  # noqa: E402
from skills_experiment.benchmark import swebench_lite  # noqa: E402
from skills_experiment.sandbox.docker import DockerSandbox  # noqa: E402

DEFAULT_INSTANCE = "pylint-dev__astroid-1268"


def _show(label: str, value: str, limit: int = 300) -> None:
    text = value.strip()
    if len(text) > limit:
        text = text[:limit] + " ..."
    print(f"  {label}: {text!r}")


def main(argv: list[str]) -> int:
    instance_id = argv[0] if argv else DEFAULT_INSTANCE
    task = swebench_lite.load_instance(instance_id, split="dev", offline=True)
    workdir = paths.REPO_ROOT / "runs" / "_sandbox_check" / instance_id

    print(f"instance : {instance_id} ({task.repo})")
    print(f"image    : {task.image}")
    print(f"workdir  : {workdir}")

    sandbox = DockerSandbox(workdir)
    ok = True
    sandbox.prepare(task)
    try:
        result = sandbox.run("pwd")
        print("\n[run]")
        _show("pwd", result.stdout)
        _show("exit", str(result.exit_code))

        result = sandbox.run("git rev-parse HEAD")
        print("\n[git]")
        _show("HEAD", result.stdout)
        _show("stderr", result.stderr)
        ok = ok and result.exit_code == 0 and bool(result.stdout.strip())

        print("\n[read_file]")
        content = sandbox.read_file("astroid/nodes/as_string.py", 1, 3)
        _show("head", content)
        ok = ok and not content.startswith("[error]")

        print("\n[list_dir]")
        listing = sandbox.list_dir("astroid")
        _show("entries", listing)
        ok = ok and not listing.startswith("[error]")

        print("\n[write_file + diff]")
        marker = "astroid/_skills_exp_probe.txt"
        write = sandbox.write_file(marker, "probe\n")
        _show("write", write)
        # clean up the probe so we do not leave state behind
        sandbox.run(f"rm -f {marker}")
        diff = sandbox.diff()
        _show("diff (empty expected)", diff)
        ok = ok and write.startswith("[ok]") and diff.strip() == ""

        print("\n[write_file + diff, non-empty]")
        write = sandbox.write_file(marker, "probe\n")
        diff = sandbox.diff()
        _show("write", write)
        _show("diff", diff)
        ok = ok and write.startswith("[ok]") and "_skills_exp_probe.txt" in diff
        sandbox.run(f"rm -f {marker}")

        print("\n[absolute container path]")
        content = sandbox.read_file("/testbed/astroid/nodes/as_string.py", 1, 2)
        _show("head", content)
        ok = ok and not content.startswith("[error]")
    finally:
        sandbox.cleanup()

    print("\nSANDBOX VALIDATION " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
