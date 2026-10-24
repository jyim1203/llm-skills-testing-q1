"""CLI path handling.

Artifacts are passed to subprocesses that run with a different working
directory (notably the SWE-bench harness). A relative ``--base-dir`` must be
resolved up front, or the harness cannot open the predictions file.
"""

from __future__ import annotations

from argparse import Namespace

from skills_experiment.cli import _base_dir


def test_base_dir_is_absolute():
    path = _base_dir(Namespace(base_dir="runs/_local-smoke"))
    assert path is not None
    assert path.is_absolute()
    assert path.name == "_local-smoke"


def test_base_dir_default_is_none():
    assert _base_dir(Namespace(base_dir="")) is None
