# Resolving a Python repository issue

Use this procedure for repository-level bug fixes and small feature changes. It
is intentionally more specific than general "best practice"; follow the steps in
order, but skip a step only when the repository gives you a concrete reason to.

## 1. Turn the report into a testable target

- Extract the exact public behaviour, error text, option name, function name,
  and input types from the issue or PR description. Treat explicit expected
  output, exception text, and stated API constraints as the specification.
- If the report includes a reproduction snippet, run it or translate it into a
  narrow test before editing.
- Identify the likely test file by searching for the named symbol, option, or
  error string. Read the test file and its `conftest.py` before reading broad
  implementation areas.

## 2. Find the repository's real test command

- Inspect `pyproject.toml`, `tox.ini`, `noxfile.py`, `Makefile`, `setup.cfg`,
  and the CI workflow to find the project's own test invocation.
- Prefer the narrowest command that exercises the affected test node over the
  full suite.
- If the suite has import or collection errors, fix the invocation or
  environment first; do not diagnose logic from a broken test harness.
- Never modify, delete, skip, or weaken tests to make them pass.

## 3. Trace the path before changing it

- Follow the code from the public entry point to the point where behaviour
  diverges from the report.
- Read the nearest callers and at least one sibling implementation that already
  handles the same pattern. Match the repository's conventions.
- For regressions, inspect recent history with `git log`, `git blame`, or
  `git log -S<symbol>` to learn what changed and which invariants mattered.
- Write down, for yourself, the root cause and the smallest observable change
  that would prove it. Do not edit until you can state both.

## 4. Make the change complete

- Change the implementation, not the test. Keep the diff focused on the
  reported behaviour.
- If the code has parallel paths, update all of them consistently: sync/async,
  encode/decode, copy/deepcopy, serialisation/deserialisation, platform
  branches, and the error path.
- When the issue introduces a public option, parameter, or exception, check its
  default, validation, documentation, and backwards-compatible behaviour.
- Check Python edge cases that commonly cause incomplete fixes: `None`, empty
  containers, booleans versus integers, mutable defaults, encoding, copy
  semantics, and exception types.
- Use targeted edits. Avoid rewriting a whole file when a small patch is enough.

## 5. Verify in widening circles

- Run the narrow failing test first. If it fails, read the traceback and revise
  the hypothesis; do not repeatedly run the same unchanged command.
- Then run the affected test module, then nearby tests that cover the same API
  or option.
- Compare both the fail-to-pass behaviour and the surrounding pass-to-pass
  behaviour; a fix that breaks an adjacent path is not finished.
- Inspect `git diff` before finishing. It should contain only intended source
  changes, no test edits, no debug prints, and no unrelated formatting.

## 6. Budget and stopping rules

- Spend the first part of the budget locating the test and the code path; by
  roughly 40% of the step budget, have a concrete hypothesis and begin the
  patch.
- After the first edit, prioritise verification over further broad searching.
- Stop once the narrow test and the relevant module pass and the diff is clean.
  Do not keep re-reading the same output or repeating a successful command.
- If a command is blocked by the environment, record that as an environment
  failure and continue with the closest runnable check rather than looping.

## 7. Final report

- State the root cause, the files changed, and the exact tests you ran.
- Report any test you could not run and why.
- If the patch is incomplete, say what remains; do not claim verification you
  did not perform.
