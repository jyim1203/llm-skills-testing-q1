# Protocol (frozen)

This document freezes the decisions that must be fixed **before** any reported
run, so that results cannot be tuned after seeing outcomes. Anything marked
*open* is a deliberate remaining choice; everything else is frozen and enforced
by code.

Scope: the pilot/setup phase (handoff §11). The main evaluation run is out of
scope here.

---

## 1. Question

> When the substantive instructions are identical, does delivering them as an
> agent *Skill* differ from pasting them directly into the prompt?

Primary contrast: **C (skill) vs B (direct prompt)**. Condition **A (baseline)**
anchors both.

## 2. Conditions

| Condition | Implementation | What varies |
|---|---|---|
| `A_baseline` | `conditions/baseline.py` | nothing beyond the task |
| `B_prompt_instructions` | `conditions/prompt_instructions.py` | workflow text pasted into the system prompt |
| `C_skill` | `conditions/skill.py` | same text packaged as `SKILL.md`, advertised by name/description, loaded on demand |

The only difference between conditions is what each `Condition.build()` returns.
Everything else (tool set, budgets, stop conditions, loop) is shared.

## 3. Single source of truth (fairness)

* `assets/prompts/workflow_instructions.md` — the experimental text.
* B injects it verbatim; C's `SKILL.md` body is generated from it.
* The runner **refuses to start** unless the two body hashes are byte-identical.
* Both hashes are recorded on every run row (`prompt_version_or_hash`,
  `skill_version_or_hash`).

Current fairness hash: `05b85856a462e78909445981407e07c8348a452aef205e9c47996f4131c4068e`.

`assets/prompts/base_system_prompt.md` is intentionally procedure-free.

## 4. Task subsets

Both frozen a priori; selection is one-instance-per-repository for topic spread.

**Main — `data/task_selection.json` (Lite `test` split, 5 tasks).**

| Instance | Repo | Topic |
|---|---|---|
| `django__django-11099` | django/django | web framework / input validation |
| `psf__requests-3362` | psf/requests | HTTP client / decoding |
| `matplotlib__matplotlib-22835` | matplotlib/matplotlib | plotting / color norms |
| `sympy__sympy-20590` | sympy/sympy | symbolic math / object model |
| `scikit-learn__scikit-learn-10297` | scikit-learn/scikit-learn | ML estimator API |

**Dev — `data/task_selection_dev.json` (Lite `dev` split, 3 tasks).**
Pipeline validation only; **never reported** as main results.

| Instance | Repo | Topic |
|---|---|---|
| `pylint-dev__astroid-1268` | pylint-dev/astroid | static analysis / AST visitor |
| `pydicom__pydicom-1256` | pydicom/pydicom | binary/medical file serialization |
| `pvlib__pvlib-python-1154` | pvlib/pvlib-python | scientific numerics |

Dataset: `SWE-bench/SWE-bench_Lite`. Records cached under `data/instances/`.
Gold `patch`/`test_patch` are eval-only and never exposed to the agent.

## 5. Model under test

* One model per experiment, pinned by exact id in `configs/models/<name>.toml`.
* `configs/models/gpt-6-luna.toml` is a **fictional placeholder** for ChatGPT;
  set a real `model_id` before any reported run.
* `params` (temperature, max tokens) are part of the protocol and recorded.
* Provider adapters: `openai`, `anthropic`, `google`, `mock`. Anthropic/Gemini
  adapters are written but must be smoke-tested with one live call each before
  use.

## 6. Budgets

Set in the experiment config (`[budgets]`): `max_steps`, `max_tokens`,
`elapsed_seconds`, `tool_timeout_seconds`. Identical across conditions so the
comparison is fair. Stop reasons are recorded per attempt.

`max_tokens` is a **cumulative** per-attempt budget (input + output summed across
steps), checked after each step. Because the loop resends the growing transcript
every step, input tokens dominate this total, so the limit must be **non-binding**
— otherwise a condition can exhaust it before writing a patch. In the dev
shakedown, condition B hit the original 120k limit at step 11 with an **empty
patch**; both configs now use `max_tokens = 600000` (still far below the model's
context window, since any single request stays small). Always check per-attempt
`stop_reason`: a `token_budget` stop is a fairness warning, not a normal
completion.

## 7. Isolation

* Fresh workspace per attempt.
* Fresh conversation per attempt.
* Condition C's `SKILL.md` is written into that attempt's own `skills/` dir; A
  and B never receive a skills dir **or** the `load_skill` tool.
* Docker sandbox gives each attempt its own container, removed on cleanup.

## 8. Grading

* Uses the **official** SWE-bench harness (`swebench.harness.run_evaluation`),
  never a reimplementation.
* **Pinned version:** `swebench==5.0.2` in a dedicated `.venv-harness`.
* Interpreter resolution: config `[harness].python` -> `$SWEBENCH_PYTHON` ->
  local `.venv-harness` -> current interpreter.
* Attempts are grouped by `(condition, attempt)`; one harness `run_id` per
  group; each instance graded in its own container.
* Per-instance test timeout and worker count are config-driven.
* The harness version is recorded on every row (`harness_version`).
* Harness logs are cleared per `run_id` before each grade so stale reports can
  never be reused.

**Platform note.** The harness is designed for Linux. On Windows it writes the
candidate patch and the in-container `eval.sh` with CRLF, which breaks the
LF-only containers (`set: pipefail\r: invalid option name`, `pytest: command
not found`). The supported fix is to run the harness under Linux/WSL. Where that
is unavailable, `evaluation/_swebench_lf_shim.py` forces verbatim newlines and is
used automatically on Windows. Validate the whole path with
`python scripts/validate_harness.py <dev-instance>` — it grades the gold patch
and must print `PASSED`.

## 9. Failure handling

Each attempt ends in exactly one `evaluation_status`:

| status | meaning | counted? | rerun? |
|---|---|---|---|
| `resolved` | patch passed the tests | yes (numerator) | no |
| `unresolved` | graded and failed (agent-attributable) | yes (denominator) | no |
| `infrastructure_error` | setup/model/harness failure, not the patch | no | yes |
| `not_evaluated` | produced a patch, not graded yet | no | n/a |

Classification rules: empty patches and patch-apply failures are **agent
failures** (`unresolved`); image pulls, container/apply crashes, and test
timeouts are **infrastructure errors**.

**Rerun policy.** An `infrastructure_error` attempt may be rerun at most
`max_reruns` times (default 1). Reruns append a **new** attempt row; existing
rows are never overwritten. Attempts that already produced a patch are re-graded
(`grade --regrade`) rather than re-run. `resolved`/`unresolved` are never rerun.

Implementation: `src/skills_experiment/evaluation/policy.py`.

## 10. Metrics and analysis plan

Primary: **resolved rate** over counted attempts, per condition.

Effects: pairwise differences vs a reference condition, with a **task-level
bootstrap 95% CI** (the task, not the attempt, is the resampling unit, because
tasks are the independent unit). Implemented in `src/skills_experiment/analysis.py`
(`analyze` command; `--resamples`, default 5000; fixed seed).

Secondary (recorded, not headline): input/output tokens, tool calls, steps,
elapsed seconds, **tests passed / total**
(parsed from the harness's per-instance reports: `FAIL_TO_PASS` / `PASS_TO_PASS`
success and failure counts), and — for C — skill discovery/load rates.

Number of repeats: **3 per (task, condition)** (frozen). All attempts per
condition are retained so the analysis can aggregate or report stability.

## 11. Run log

One row per attempt, matching handoff §12, in
`runs/<experiment_id>/runs.{csv,jsonl}`. Grading and reruns update/append rows in
place. Full artifacts (patch, transcript, condition definition, result) live
under `runs/<experiment_id>/attempts/...`. Secrets are never logged.

## 12. Open items (must be decided before the main run)

* Which model + exact pinned version is the study's fixed model?
* How many main tasks (the current subset is 5; 20/25/30 are the candidates)?
* Random vs. stratified main-phase sampling (this pilot is one-per-repo).
* Confirm the local `python-repo-maintenance` skill wording is the frozen text.

Decided: **3 repeats per (task, condition)**; **A/B/C only** (no fourth
"pre-loaded skill" condition); reported runs execute under **Linux/WSL**.

**Reproducibility anchors (frozen):** dataset revision pinned to the sha
`b0dde1093fe417d83b7184254edf8199c1f0dff5`; `data/instances/` is committed so the
task bytes are versioned; every run records a `benchmark_dataset_hash` and writes
`dataset_manifest.json`; every attempt records its Docker image digest, RNG seed,
UTC start time, and the framework git commit. `preflight` pulls/verifies images
before a run.

## 12a. Platform: Linux/WSL

The SWE-bench harness is supported on Linux; reported main runs execute there.

**Environment (set up and validated):** WSL2 distro `Ubuntu` (default), with
Docker Desktop WSL integration enabled, so the distro shares the Docker engine
and cached SWE-bench images. The harness venv is CPython 3.11 +
`swebench==5.0.2` at `/root/skills-harness`, wired via `SWEBENCH_PYTHON`
(`/etc/profile.d/skills-harness.sh`). Created by
`scripts/wsl_setup_harness.sh`; validated by grading the gold patch on a dev
instance (`VALIDATION PASSED`) and by a full attempt -> grade cycle.

On Windows the harness needs the `evaluation/_swebench_lf_shim.py` fallback
(validated on the gold patch), which is acceptable for setup/dev but not the
target platform for reported results.

## 13. Setup-phase validation status (handoff §11)

Everything below the model/credentials line is validated; the remaining work is
decisions plus one live call.

* ✅ Docker sandbox validated end to end on a real dev image
  (`python scripts/validate_sandbox.py`): container start, exec, read/write/list,
  patch capture. On Windows this required POSIX container paths and UTF-8 output
  decoding (see `sandbox/docker.py`).
* ✅ Official harness `swebench==5.0.2` resolves the gold patch
  (`python scripts/validate_harness.py pylint-dev__astroid-1268` → `PASSED`) —
  confirmed on **both** Windows (LF shim) and **Linux/WSL** (native).
* ✅ Full attempt → grade → analyze cycle exercised on the real docker sandbox
  with the mock model, on Windows and in WSL; the run log updates in place and
  empty patches classify as `unresolved`.
* ✅ 35 unit tests pass; fairness hashes match.
* ⏳ No provider SDK in the agent environment and no `.env` for the fixed study
  model; the study model ids are still placeholders. (For shakedown runs, the
  OpenAI SDK is installed in the Linux harness venv and `.env` holds a Groq key;
  see the model-under-test note below.)

### Model access note (setup phase)

* OpenCode's free tier (`opencode/deepseek-v4.1-flash-free`) **cannot** drive the
  harness: its inference API rejects non-OpenCode clients (`FreeTierError`), and
  the local OpenCode server only exposes text generation (no tool calling, no
  token usage).
* Shakedown model: **`deepseek-flash`** (DeepSeek's OpenAI-compatible API; tool
  calling + usage verified) run via the Linux/WSL path. This is a *dev* model
  only — the study's fixed model is still an open item (§12).
* Groq's free tier (`groq-gpt-oss-120b`) turned out **unusable** for the agent
  loop: 8,000 TPM / 200,000 TPD per model, while a single request already
  exceeds 8K tokens (HTTP 413). Kept in `configs/models/` for Dev-Tier use.
* ✅ Dev shakedown (astroid, `deepseek-flash`, 3 conditions × 1 repeat) ran end to
  end on Linux/WSL with the official harness: 3/3 attempts produced patches, 0
  infrastructure errors, and per-attempt time / tokens / tests-passed were
  recorded. n=1 per condition — this validates plumbing, it is **not** a result.

