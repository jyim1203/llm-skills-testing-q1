#!/usr/bin/env python
"""Validate the SWE-bench harness integration end to end.

    python scripts/validate_harness.py pylint-dev__astroid-1268

Writes a predictions file containing the **gold** patch for one dev instance,
runs the official harness through :mod:`skills_experiment.evaluation.harness`,
and reports the outcome. A correct setup resolves the instance. This proves the
Docker images, test environment, and our report parsing all work before any
model spend.

Dev instances only. Never use gold patches for reported results.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skills_experiment import paths  # noqa: E402
from skills_experiment.benchmark import swebench_lite  # noqa: E402
from skills_experiment.evaluation import harness  # noqa: E402

DEFAULT_INSTANCE = "pylint-dev__astroid-1268"


def main(argv: list[str]) -> int:
    instance_id = argv[0] if argv else DEFAULT_INSTANCE
    task = swebench_lite.load_instance(instance_id, split="dev", offline=True)
    if not task.patch.strip():
        print(f"{instance_id}: no gold patch in cache; cannot validate.")
        return 2

    python = harness.resolve_harness_python("")
    print(f"harness interpreter : {python}")
    print(f"harness version     : {harness.harness_version(python)}")
    print(f"instance            : {instance_id} ({task.repo})")
    print(f"image               : {task.image}")

    work_dir = paths.REPO_ROOT / "runs" / "_harness_validation" / instance_id
    run_id = f"validate-{instance_id}"
    # Start clean: the harness skips instances that already have a report.
    import shutil

    stale = work_dir / "logs" / "run_evaluation" / run_id
    if stale.exists():
        shutil.rmtree(stale, ignore_errors=True)
    pred_path = harness.write_predictions(
        [
            harness.Prediction(
                instance_id=instance_id,
                model_name_or_path="gold",
                model_patch=task.patch,
            )
        ],
        work_dir / "predictions.jsonl",
    )
    print(f"predictions         : {pred_path}")

    result = harness.run_harness(
        predictions_path=pred_path,
        run_id=run_id,
        dataset="SWE-bench/SWE-bench_Lite",
        split="dev",
        instance_ids=[instance_id],
        python=python,
        max_workers=1,
        timeout=1800,
        work_dir=work_dir,
        report_dir=work_dir / "reports",
    )
    print(f"exit code           : {result.returncode}")
    print(f"report              : {result.report_path}")
    print(f"resolved            : {result.resolved_ids}")
    print(f"unresolved          : {result.unresolved_ids}")
    print(f"errors              : {result.error_ids}")

    ok = instance_id in result.resolved_ids
    print("\nVALIDATION " + ("PASSED" if ok else "FAILED") + " (gold patch)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
