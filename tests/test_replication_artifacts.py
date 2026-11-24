"""The committed mechanism-study artifacts must keep verifying.

This is the CI guard for `scripts/verify_replication.py`: if a later change
edits a prompt, a plan, or a results file so that the committed artifacts stop
agreeing with each other, this test fails. It needs no Docker, network, or API
key.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_replication.py"


def test_committed_artifacts_pass_replication_checks() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, f"{proc.stdout}\n{proc.stderr}"
    assert "PASSED" in proc.stdout
