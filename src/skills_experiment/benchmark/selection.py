"""Task subsets for the study.

Two curated subsets, both frozen *before* outcomes are examined:

* ``MAIN_TASKS``  -- the 5-instance Lite **test**-split subset used for the
  experiment proper (one instance per repository, wide topic spread).
* ``DEV_TASKS``   -- 3 Lite **dev**-split instances used only for smoke-testing
  the full pipeline (setup, patch capture, grading). Dev results are never
  reported as main results.

Selection procedure is documented here and in ``PROTOCOL.md`` and is decided
before looking at any condition outcomes (handoff section 6).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .. import paths

# --------------------------------------------------------------------------- #
# Main subset -- one instance per repository, test split
# --------------------------------------------------------------------------- #
MAIN_TASKS: list[dict[str, str]] = [
    {
        "instance_id": "django__django-11099",
        "repo": "django/django",
        "topic": "web framework / input validation (regex)",
        "why": "Django exercises a large, mature codebase with a subtle regex-validation bug.",
    },
    {
        "instance_id": "psf__requests-3362",
        "repo": "psf/requests",
        "topic": "HTTP client / response decoding semantics",
        "why": "Small, widely used networking library; behavior is easy to reason about.",
    },
    {
        "instance_id": "matplotlib__matplotlib-22835",
        "repo": "matplotlib/matplotlib",
        "topic": "plotting / color-normalization edge cases",
        "why": "Numerics + API surface differ from pure logic bugs.",
    },
    {
        "instance_id": "sympy__sympy-20590",
        "repo": "sympy/sympy",
        "topic": "symbolic math core / object model (Symbol __dict__)",
        "why": "Core object-model bug in a computer-algebra system; a distinct problem type.",
    },
    {
        "instance_id": "scikit-learn__scikit-learn-10297",
        "repo": "scikit-learn/scikit-learn",
        "topic": "ML estimator / model-selection API",
        "why": "Adds an ML library and a parameter-handling bug to the mix.",
    },
]

# Backwards-compatible alias.
SELECTED_TASKS = MAIN_TASKS

# --------------------------------------------------------------------------- #
# Dev subset -- for smoke tests only, dev split
# --------------------------------------------------------------------------- #
DEV_TASKS: list[dict[str, str]] = [
    {
        "instance_id": "pylint-dev__astroid-1268",
        "repo": "pylint-dev/astroid",
        "topic": "static analysis / AST visitor",
        "why": "Small, pure-Python logic fix; good for validating the end-to-end cycle.",
    },
    {
        "instance_id": "pydicom__pydicom-1256",
        "repo": "pydicom/pydicom",
        "topic": "binary/medical file format serialization",
        "why": "Data-structure/serialization bug; different failure surface from astroid.",
    },
    {
        "instance_id": "pvlib__pvlib-python-1154",
        "repo": "pvlib/pvlib-python",
        "topic": "scientific numerics (irradiance model)",
        "why": "Numeric edge-case fix; adds a scientific-computing repo to the smoke set.",
    },
]


def selected_instance_ids() -> list[str]:
    return [t["instance_id"] for t in MAIN_TASKS]


def dev_instance_ids() -> list[str]:
    return [t["instance_id"] for t in DEV_TASKS]


def build_selection(
    tasks: Optional[list[dict[str, str]]] = None,
    *,
    subset: str = "main",
    dataset: str = "SWE-bench/SWE-bench_Lite",
    dataset_revision: str = "main",
    split: str = "test",
    seed: int = 20261015,
) -> dict[str, Any]:
    """Assemble a selection document (metadata + frozen task list)."""
    tasks = tasks if tasks is not None else (DEV_TASKS if subset == "dev" else MAIN_TASKS)
    return {
        "subset": subset,
        "dataset": dataset,
        "dataset_revision": dataset_revision,
        "split": split,
        "selection_procedure": "one instance per repository, fixed a priori",
        "seed": seed,
        "num_tasks": len(tasks),
        "tasks": tasks,
    }


def write_selection(
    path: Optional[str | Path] = None, *, subset: str = "main", **kwargs: Any
) -> Path:
    if path is None:
        filename = "task_selection_dev.json" if subset == "dev" else "task_selection.json"
        target = paths.DATA_DIR / filename
    else:
        target = Path(path)
    if not target.is_absolute():
        target = paths.REPO_ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    document = build_selection(subset=subset, **kwargs)
    target.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return target
