"""Thin wrapper around the official SWE-bench evaluation harness.

We do not reimplement grading. Instead we:

1. write a predictions file (``instance_id``/``model_name_or_path``/``model_patch``)
   from captured patches;
2. invoke ``python -m swebench.harness.run_evaluation`` as a subprocess, using a
   dedicated interpreter (the harness has heavy deps); and
3. parse the aggregate report it writes.

Pinning the harness version is part of the protocol -- the exact version is
recorded on every run row (``harness_version``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


class HarnessError(RuntimeError):
    """Raised when the harness cannot be invoked or produces no report."""


@dataclass
class Prediction:
    instance_id: str
    model_name_or_path: str
    model_patch: str

    def to_dict(self) -> dict[str, str]:
        return {
            "instance_id": self.instance_id,
            "model_name_or_path": self.model_name_or_path,
            "model_patch": self.model_patch,
        }


@dataclass
class HarnessResult:
    run_id: str
    returncode: int
    report_path: Optional[Path] = None
    resolved_ids: list[str] = field(default_factory=list)
    unresolved_ids: list[str] = field(default_factory=list)
    error_ids: list[str] = field(default_factory=list)
    infra_failure_ids: list[str] = field(default_factory=list)
    empty_patch_ids: list[str] = field(default_factory=list)
    failure_reasons: dict[str, str] = field(default_factory=dict)
    # Per-instance test tallies parsed from the per-instance report.json files
    # (the aggregate report only carries resolved/unresolved ids).
    test_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_report: dict[str, Any] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""

    def status_for(self, instance_id: str) -> str:
        """Coarse outcome for one instance: resolved | unresolved | error | missing."""
        if instance_id in self.resolved_ids:
            return "resolved"
        if instance_id in self.unresolved_ids:
            return "unresolved"
        if instance_id in self.error_ids:
            return "error"
        return "missing"


def resolve_harness_python(configured: str = "") -> str:
    """Pick the interpreter used to run the harness.

    Priority: explicit config value -> ``$SWEBENCH_PYTHON`` -> a local
    ``.venv-harness`` venv if present -> current interpreter.
    """
    if configured:
        return configured
    env = os.environ.get("SWEBENCH_PYTHON", "").strip()
    if env:
        return env
    # A dedicated harness venv is the recommended setup; use it if it exists.
    from .. import paths

    for rel in (
        Path(".venv-harness") / "Scripts" / "python.exe",
        Path(".venv-harness") / "bin" / "python",
    ):
        candidate = paths.REPO_ROOT / rel
        if candidate.exists():
            return str(candidate)
    return sys.executable


def harness_command(python: str) -> list[str]:
    """Command prefix that runs the harness.

    On Windows the harness corrupts the LF-only container files (see
    ``_swebench_lf_shim``), so we route through a small LF-forcing shim. On other
    platforms we invoke the module directly.
    """
    if os.name == "nt":
        shim = Path(__file__).with_name("_swebench_lf_shim.py")
        if shim.exists():
            return [python, str(shim)]
    return [python, "-m", "swebench.harness.run_evaluation"]


def harness_version(python: str) -> str:
    """Best-effort version string of the harness package (for run logs)."""
    try:
        out = subprocess.run(
            [python, "-c", "import swebench, importlib.metadata as m; print(m.version('swebench'))"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # noqa: BLE001 - version is best-effort
        pass
    return ""


def write_predictions(predictions: Iterable[Prediction], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for pred in predictions:
            fh.write(json.dumps(pred.to_dict()) + "\n")
    return target


def _find_report(report_dir: Path, run_id: str, workflow: Path) -> Optional[Path]:
    """Locate the aggregate report across harness versions/schemas."""
    candidates: list[Path] = []
    if report_dir.exists():
        candidates += sorted(report_dir.glob(f"*{run_id}*.json"))
        candidates += sorted(report_dir.glob("results.json"))
    # newer harness writes to logs/run_evaluation/<run_id>/results.json
    candidates += sorted((workflow / "logs" / "run_evaluation" / run_id).glob("results.json"))
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


_TEST_STATUS_GROUPS = ("FAIL_TO_PASS", "PASS_TO_PASS", "FAIL_TO_FAIL", "PASS_TO_FAIL")


def collect_test_stats(
    work_dir: str | Path,
    run_id: str,
    instance_ids: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """Per-instance test tallies from the harness's per-instance reports.

    The aggregate report only lists resolved/unresolved ids; the *counts* of
    tests that passed live in
    ``logs/run_evaluation/<run_id>/<model>/<instance>/report.json`` under
    ``tests_status``. Returns ``{instance_id: {...}}`` (missing when absent, e.g.
    an empty patch that never ran tests).
    """
    base = Path(work_dir) / "logs" / "run_evaluation" / run_id
    stats: dict[str, dict[str, Any]] = {}
    for instance_id in instance_ids:
        matches = sorted(base.glob(f"*/{instance_id}/report.json"))
        if not matches:
            continue
        try:
            data = json.loads(matches[0].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entry = data.get(instance_id, data) if isinstance(data, dict) else {}
        tests_status = (entry or {}).get("tests_status") or {}
        detail = {group: {"passed": 0, "failed": 0} for group in _TEST_STATUS_GROUPS}
        for group in _TEST_STATUS_GROUPS:
            block = tests_status.get(group) or {}
            detail[group]["passed"] = len(block.get("success") or [])
            detail[group]["failed"] = len(block.get("failure") or [])
        passed = sum(d["passed"] for d in detail.values())
        total = sum(d["passed"] + d["failed"] for d in detail.values())
        stats[instance_id] = {
            "tests_passed": passed,
            "tests_total": total,
            "fail_to_pass_passed": detail["FAIL_TO_PASS"]["passed"],
            "fail_to_pass_total": (
                detail["FAIL_TO_PASS"]["passed"] + detail["FAIL_TO_PASS"]["failed"]
            ),
            "pass_to_pass_passed": detail["PASS_TO_PASS"]["passed"],
            "pass_to_pass_total": (
                detail["PASS_TO_PASS"]["passed"] + detail["PASS_TO_PASS"]["failed"]
            ),
            "tests_detail": detail,
        }
    return stats


def run_harness(
    *,
    predictions_path: str | Path,
    run_id: str,
    dataset: str,
    split: str,
    instance_ids: Optional[list[str]] = None,
    python: str = "",
    max_workers: int = 4,
    timeout: int = 1800,
    work_dir: str | Path,
    report_dir: Optional[str | Path] = None,
    extra_args: Optional[list[str]] = None,
    subprocess_timeout: Optional[int] = None,
) -> HarnessResult:
    """Invoke the harness for one predictions file and parse its report."""
    py = resolve_harness_python(python)
    # The harness runs with cwd=work_dir, so every path crossing that boundary
    # must be absolute or it will be resolved against the wrong directory.
    predictions_path = Path(predictions_path).expanduser().resolve()
    work_dir = Path(work_dir).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    report_dir = (
        Path(report_dir).expanduser().resolve()
        if report_dir
        else (work_dir / "reports")
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        *harness_command(py),
        "-d",
        dataset,
        "-s",
        split,
        "-p",
        str(predictions_path),
        "-id",
        run_id,
        "--max_workers",
        str(max_workers),
        "-t",
        str(timeout),
        "--report_dir",
        str(report_dir),
    ]
    if instance_ids:
        cmd += ["-i", *instance_ids]
    cmd += list(extra_args or [])

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=subprocess_timeout,
        )
    except FileNotFoundError as exc:
        raise HarnessError(
            f"Could not launch the harness interpreter {py!r}. "
            f"Create the harness venv (see README) or set SWEBENCH_PYTHON."
        ) from exc

    report_path = _find_report(report_dir, run_id, work_dir)
    result = HarnessResult(
        run_id=run_id,
        returncode=proc.returncode,
        report_path=report_path,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
    if report_path is None:
        raise HarnessError(
            f"Harness produced no report for run '{run_id}' (exit {proc.returncode}).\n"
            f"--- stdout tail ---\n{(proc.stdout or '')[-2000:]}\n"
            f"--- stderr tail ---\n{(proc.stderr or '')[-2000:]}"
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    result.raw_report = report
    result.resolved_ids = list(report.get("resolved_ids", []))
    result.unresolved_ids = list(report.get("unresolved_ids", []))
    result.error_ids = list(report.get("error_ids", []))
    result.infra_failure_ids = list(report.get("infra_failure_ids", []))
    result.empty_patch_ids = list(report.get("empty_patch_ids", []))
    result.failure_reasons = dict(report.get("failure_reasons", {}))
    result.test_stats = collect_test_stats(
        work_dir, run_id, report.get("submitted_ids") or []
    )
    return result
