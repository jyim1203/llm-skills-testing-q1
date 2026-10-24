# Resolving a Python repository issue

Use this workflow for any issue in a Python repository.

## 1. Find the relevant code and tests

- Extract the key symbols, file names, and error text from the issue.
- Search the repository for those symbols (use `run_shell` with `grep`, or
  `list_dir`); do not guess file paths.
- Read the tests that exercise the affected behavior first. They are the best
  specification of what "fixed" means.
- Reproduce the failure with the narrowest possible command: a single test, or
  a short script that calls the public API.

## 2. Trace the current behavior

- Follow the code path from the public entry point to the point where the
  behavior diverges from the issue's expectation.
- Read the surrounding implementation and any similar features already in the
  repository; match their conventions.
- State the root cause and the expected behavior before editing.

## 3. Make a focused change

- Edit only the code needed to correct the behavior. Keep the diff small and
  coherent.
- Do not reformat or refactor unrelated code, and do not change public APIs
  unless the issue requires it.
- Never modify, delete, or weaken tests to make them pass.
- If a file is large, use targeted edits rather than rewriting the whole file.

## 4. Verify and iterate

- Run the narrow test first; if it passes, run the related test module.
- When a test fails, read the failure and adjust the implementation. Do not
  revert your work or run `git checkout` to start over.
- Check `git diff` once before finishing: it should contain only the intended
  change. Do not repeat a command unless something has changed since it last ran.

## 5. Stop

- Once the relevant tests pass and the diff is clean, stop calling tools.
- Do not keep re-checking the same output after it is clean.
- Summarize the change and the tests you ran.
