# Task Selection and 20-Task Extension Plan

Status: planning note. The reported six-task study (`main-local-01`) remains
frozen; this document describes criteria for adding tasks without changing the
existing runs.

## Project in brief

The project tests whether delivering the same workflow instructions as an agent
*Skill* changes coding-agent performance relative to putting those instructions
directly in the prompt.

| Condition | What the agent gets |
|---|---|
| **A — baseline** | Task and repository context only |
| **B — direct prompt** | A plus the workflow instructions in the system prompt |
| **C — skill** | A plus the same instructions packaged as `SKILL.md` and loaded on demand |

The primary contrast is **C vs B**. The reported experiment uses Qwen 3.5 9B
Q4_K_M on six SWE-bench Lite tasks with five repeats per condition (90 attempts).
It resolved 46/90 attempts: A 16/30, B 15/30, C 15/30. The C-B difference was
0.0 percentage points. See
[`results/main-local-01/RESULTS.md`](results/main-local-01/RESULTS.md) and
[`PROTOCOL-main-local.md`](PROTOCOL-main-local.md).

## Selection criteria

The original six tasks were fixed before outcomes were examined. New tasks
should follow the same rules and be frozen before their first attempt.

1. **Dataset and split.** Use `SWE-bench/SWE-bench_Lite`, `test` split, at
   revision `b0dde1093fe417d83b7184254edf8199c1f0dff5`.
2. **Valid evaluation data.** Each instance must have a gold patch, a test
   patch, at least one FAIL_TO_PASS test, and a usable PASS_TO_PASS set.
3. **Runnable environment.** The SWE-bench Docker image must build or pull
   reliably, the test suite must run inside the 1,800-second harness timeout, and
   the task must not require external services, network access, or a GPU.
4. **Bounded, non-trivial fix.** Prefer a small-to-medium gold patch (roughly
   1-3 files; not a one-line change) with a clear behavioral target. Do not use
   patch size alone as a difficulty proxy: the existing `pytest` task was one
   file and 25 changed lines, but it behaved as a floor.
5. **Domain diversity.** Avoid duplicating the existing repositories. Add
   domains not already represented: CLI/tooling, serialization, async/network,
   dataframes, packaging, security, databases, or developer tooling.
6. **One instance per repository.** The current six tasks come from six
   repositories. Maintaining this rule for 20 tasks requires **20 distinct
   repositories**.
7. **No leakage.** Do not use tasks whose issue text, tests, or patches were
   shown to the model during prompt/skill development. Gold patches and test
   patches remain eval-only.
8. **Consistent hint policy.** If hints are used, apply the same policy to every
   task and record it; do not add hints selectively after seeing results.
9. **No outcome-based selection.** Select and freeze task IDs before examining
   new A/B/C outcomes. Do not drop tasks because they are easy, hard, or
   inconvenient after the run starts.

## Tasks already in the study

| Instance | Repository | Topic | Observed A/B/C |
|---|---|---|---|
| `django__django-11099` | django/django | web framework / input validation | 5/5, 5/5, 5/5 (ceiling) |
| `psf__requests-3362` | psf/requests | HTTP client / decoding | 4/5, 5/5, 5/5 (discriminating) |
| `matplotlib__matplotlib-22835` | matplotlib/matplotlib | plotting / color norms | 0/5, 0/5, 0/5 (floor) |
| `sympy__sympy-20590` | sympy/sympy | symbolic math / object model | 2/5, 0/5, 0/5 (discriminating) |
| `scikit-learn__scikit-learn-10297` | scikit-learn/scikit-learn | ML estimator API | 5/5, 5/5, 5/5 (ceiling) |
| `pytest-dev__pytest-5495` | pytest-dev/pytest | test framework / assertion rewriting | 0/5, 0/5, 0/5 (floor) |

Four of the six tasks were at ceiling or floor in every condition: 60 of the 90
attempts provided no condition discrimination. Only `requests` and `sympy`
varied. The next task set should therefore favor tasks with a realistic chance
of producing both resolved and unresolved attempts, while still avoiding
outcome-based cherry-picking.

## Target design

The current set has **six** tasks. Adding **10** tasks would produce **16**
tasks, not 20. To reach 20 while keeping one instance per repository, add
**14** new tasks.

| Design | Attempts | Notes |
|---|---:|---|
| Current 6 tasks x 3 conditions x 5 repeats | 90 | Already completed |
| 20 tasks x 3 conditions x 3 repeats | 180 | Preferred extension |
| 20 tasks x 3 conditions x 2 repeats | 120 | Cheaper fallback |
| 16 tasks x 3 conditions x 3 repeats | 144 | If only 10 tasks are added |
| 16 tasks x 3 conditions x 2 repeats | 96 | If only 10 tasks are added |

Three repeats are preferable to two because they give a slightly less coarse
within-task view. Twenty tasks is still a small task-level sample; treat the
result as scoped to this set.

## Keeping the existing runs

Do not modify `runs/main-local-01/`, `data/task_selection_local.json`, or the
reported `main-local-01` protocol. The existing 90 attempts and the committed
result summary should remain the frozen six-task study.

**Recommended:** create a new expansion experiment containing only the new
tasks, for example:

- selection: `data/task_selection_expansion.json`
- experiment: `configs/experiments/main-local-expansion.toml`
- design: 14 new tasks x 3 conditions x 3 repeats = 126 new attempts
- image lock: a new `data/image_locks/main-local-expansion.json`

Then combine those attempts with the **first three repeats** of each existing
task for the primary 20-task analysis: 54 existing attempts + 126 new attempts =
180. The existing fourth and fifth repeats remain available as a robustness
check. For a two-repeat design, use the first two existing repeats and run 84
new attempts (120 total).

This avoids resetting the old run directory and preserves its `plan.json`,
`runs.jsonl`, and patches. The combined analysis must account for the fact that
the old first three repeats were run in blocks, while new repeats can be
interleaved normally.

A single expanded `main-local-01` run with `--resume` is possible, but it would
change that experiment's selection, repeat count, plan, dataset manifest, and
image lock. It is not recommended for the reported six-task result.

## Before running the extension

- Freeze the new task IDs and metadata in the expansion selection file.
- Pull and lock the new Docker images with
  `preflight --experiment main-local-expansion --write-lock`.
- Recheck the B/C fairness hash; it must remain unchanged.
- Record the model tag/digest, code commit, dataset revision, and image digests.
- Keep the old six-task selection and run artifacts untouched.
