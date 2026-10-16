"""Windows LF shim for the SWE-bench harness.

The official harness writes the candidate patch and the in-container eval script
with ``Path.write_text``. On Windows, text-mode writes translate ``\\n`` to
``\\r\\n``, and the LF-only Linux evaluation containers then fail with errors like
``set: pipefail\\r: invalid option name``, ``cd $'/testbed\\r'``, and
``pytest: command not found``.

The supported setup is to run the harness on Linux (or WSL). Where that is not
available, this shim forces verbatim newlines on text writes and then runs the
harness unchanged. It uses only the standard library, so the harness venv can
execute it directly:

    python <this file> -d SWE-bench/SWE-bench_Lite -s dev -p preds.jsonl -id run

It is a no-op on non-Windows platforms (it is only used there).
"""

from __future__ import annotations

import builtins
import pathlib
import runpy

_original_write_text = pathlib.Path.write_text
_original_open = builtins.open


def _write_text(self, data, encoding=None, errors=None, newline=None):  # type: ignore[no-untyped-def]
    # Never translate \n -> os.linesep: the files are consumed by Linux tools.
    return _original_write_text(self, data, encoding=encoding, errors=errors, newline="")


def _open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, *args, **kwargs):  # type: ignore[no-untyped-def]
    if newline is None and mode and ("w" in mode or "a" in mode) and "b" not in mode:
        newline = ""
    return _original_open(file, mode, buffering, encoding, errors, newline, *args, **kwargs)


def install() -> None:
    pathlib.Path.write_text = _write_text  # type: ignore[method-assign]
    builtins.open = _open  # type: ignore[assignment]


if __name__ == "__main__":
    install()
    runpy.run_module("swebench.harness.run_evaluation", run_name="__main__", alter_sys=True)
