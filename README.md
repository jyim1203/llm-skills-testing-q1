# Skills vs. Prompt Instructions — SWE-bench Lite

Scaffolding for an exploratory study of a single question:

> **When the substantive instructions are identical, does delivering them as an
> agent *Skill* differ from pasting them directly into the prompt?**

The study compares three conditions on the same SWE-bench Lite tasks:

| Condition | What the agent gets |
|---|---|
| **A — baseline** | Task + repo context only |
| **B — direct prompt** | A + the workflow instructions pasted into the system prompt |
| **C — skill** | A + the *same* instructions packaged as `SKILL.md`, advertised by name/description and loaded on demand |

The primary comparison is **C vs B** (skill delivery vs. equivalent direct
instructions). Condition A anchors the comparison.

This repo currently covers **setup, the agent framework, and model access**.
The main evaluation phase is intentionally out of scope for now.

---

## Quick start (no third-party packages required)

The core framework has **zero dependencies** — configs use the stdlib `tomllib`
parser and provider SDKs are imported lazily. From the repo root, use the
`scripts/` wrappers (they add `src/` to the path, so no install is needed):

```bash
python scripts/list_models.py            # 1. see the available models
python scripts/build_skill.py            # 2. (re)generate SKILL.md from the workflow source
python scripts/plan.py --experiment pilot  # 3. inspect the run matrix + fairness hashes
python scripts/smoke.py                  # 4. run the whole pipeline offline (mock model)
```

`smoke` runs all three conditions on the first task with the **mock** model and
an in-memory sandbox, then writes a run log to `runs/`. This is the fastest way
to confirm the plumbing works.

Once Docker and the harness are set up (see below):

```bash
python -m skills_experiment select-tasks --dev --cache   # dev/smoke subset
python -m skills_experiment run  --experiment pilot-dev   # attempt -> patch
python -m skills_experiment grade --experiment pilot-dev  # patch -> resolved/unresolved
python -m skills_experiment analyze --experiment pilot-dev
```

With `pip install -e .` the same commands are available as
`python -m skills_experiment <command>` / the `skills-exp` entry point.

---

## How to swap models (the priority)

Models are **config, not code**. Each model is one TOML file in
`configs/models/`:

```toml
# configs/models/gpt-6-luna.toml
name = "gpt-6-luna"
provider = "openai"          # openai | anthropic | google | mock
model_id = "gpt-6-luna"      # <-- the real, pinned model id
api_key_env = "OPENAI_API_KEY"
[params]
temperature = 0.0
max_tokens = 8192
```

Switch model under test by changing **one line** in `configs/experiments/pilot.toml`:

```toml
[experiment]
model = "claude-opus"   # or "gemini-pro", "gpt-6-luna", "mock"
```

…or override it on the command line:

```bash
python -m skills_experiment run --experiment pilot --model claude-opus
```

### Included profiles

| Profile | Provider | Notes |
|---|---|---|
| `gpt-6-luna` | `openai` | **Placeholder** (fictional name) standing in for ChatGPT |
| `claude-opus` | `anthropic` | Claude Opus (pin the exact snapshot) |
| `gemini-pro` | `google` | Gemini (`google-genai` SDK) |
| `deepseek-flash` | `openai` | DeepSeek V4.1 Flash via `api.deepseek.com` (cheap; shakedowns) |
| `groq-gpt-oss-120b` | `openai` | Groq free tier, `openai/gpt-oss-120b` — tool calling works, but 8K TPM free cap is too low for agent runs |
| `mock` | `mock` | Deterministic, offline, no credentials |

### Why it's easy to swap

- One interface: `skills_experiment.models.base.ModelClient`.
- One normalization layer: `Message` / `ToolCall` / `ModelResponse` / `Usage`.
- One registry: `skills_experiment.models.registry.get_registry()`.
- The agent loop and conditions never import a provider SDK.

### Adding a provider or a new model

- **New model, existing provider:** drop a new TOML file in `configs/models/`.
- **New provider:** add an adapter implementing `ModelClient` and register a
  factory in `models/registry.py` (`_FACTORY_REGISTRY`). Nothing else changes.

### Credentials

Copy `.env.example` → `.env` and set only the keys you use. The framework loads
`.env` without overriding your shell, and **never writes keys into run logs**.

---

## Repository layout

```text
configs/
  models/          one TOML per model  <-- swap models here
  conditions/      A/B/C definitions (+ fairness wiring)
  experiments/     pilot.toml, pilot-dev.toml (model, budgets, dataset, sandbox, harness)
data/
  task_selection.json      the frozen 5-task main subset + metadata
  task_selection_dev.json  the 3-task dev/smoke subset (never reported)
  instances/               cached SWE-bench Lite records (git-ignored)
src/skills_experiment/
  models/          ModelClient + registry + openai/anthropic/gemini/mock
  conditions/      baseline / prompt_instructions / skill
  agent/           tool-using loop + tool set
  sandbox/         local / docker / noop (isolation boundary)
  benchmark/       SWE-bench Lite loader + task selection (main + dev)
  evaluation/      official SWE-bench harness wrapper + failure policy
  runlog/          one row per attempt (handoff schema)
  analysis.py      per-condition stats + task-level bootstrap effects
  runner.py        tasks x conditions x repeats, fully isolated
  cli.py           list-models | build-skill | select-tasks | plan | run | grade | rerun | analyze | smoke
  assets/          base system prompt + workflow instructions (+ generated SKILL.md)
scripts/           thin CLI wrappers (+ validate_harness.py, validate_sandbox.py, wsl_setup_harness.sh)
tests/             registry, fairness, conditions, loop, isolation, policy, analysis
PROTOCOL.md        the frozen protocol (decide-before-running record)
```

---

## Conditions and isolation

The only thing that differs between conditions is what each `Condition.build()`
returns — a system prompt, a tool list, and a task message. Everything else is
shared. Guarantees:

- **Fresh workspace per attempt.** `runs/<exp>/work/<instance>/<condition>/attempt_XX/`.
- **Fresh conversation per attempt.** No messages are reused across attempts.
- **Skill isolation.** Condition C writes `SKILL.md` into *its own*
  `skills/` folder. Conditions A and B never get a skills directory **and** never
  get the `load_skill` tool.
- **Fairness assertion.** The runner refuses to start if Condition B's injected
  text and Condition C's skill body are not byte-identical.

### Fairness: one source of truth

`assets/prompts/workflow_instructions.md` is the **single** copy of the
experimental text. B injects it verbatim; C's `SKILL.md` body is generated from
it (`build-skill`). Both hashes are recorded in every run row.

`assets/prompts/base_system_prompt.md` is deliberately *procedure-free* so it
cannot contaminate the baseline.

---

## The task subset (5 instances, wide topic spread)

One instance per repository, from the official Lite **test** split, frozen a
priori (`data/task_selection.json`):

| Instance | Repo | Topic |
|---|---|---|
| `django__django-11099` | django/django | web framework / input validation |
| `psf__requests-3362` | psf/requests | HTTP client / decoding |
| `matplotlib__matplotlib-22835` | matplotlib/matplotlib | plotting / color norms |
| `sympy__sympy-20590` | sympy/sympy | symbolic math / object model |
| `scikit-learn__scikit-learn-10297` | scikit-learn/scikit-learn | ML estimator API |

Records are fetched from the HuggingFace datasets-server API and cached under
`data/instances/`. The gold `patch` / `test_patch` are cached for evaluation but
are **never** exposed to the agent (`TaskInstance.agent_view()`).

A separate 3-task **dev** subset (`data/task_selection_dev.json`, Lite `dev`
split) exists only to validate the pipeline end to end:

| Instance | Repo | Topic |
|---|---|---|
| `pylint-dev__astroid-1268` | pylint-dev/astroid | static analysis / AST visitor |
| `pydicom__pydicom-1256` | pydicom/pydicom | binary/medical file serialization |
| `pvlib__pvlib-python-1154` | pvlib/pvlib-python | scientific numerics |

Dev results are never reported as main results.

---

## Running for real (once you're ready)

```bash
pip install -e ".[openai]"        # or .[anthropic] / .[google]
cp .env.example .env              # add your key
python scripts/select_tasks.py --cache
python -m skills_experiment run --experiment pilot --model gpt-6-luna
```

**Docker is required** for trustworthy runs (the `docker` sandbox uses each
task's SWE-bench image). The `local` sandbox is for smoke tests only — it does
not reproduce the benchmark environment.

### Grading harness setup

Grading uses the **official** SWE-bench harness, not a reimplementation. It has
heavy dependencies, so it lives in its own venv (pinned to `swebench==5.0.2`):

```bash
python -m venv .venv-harness
.venv-harness/Scripts/python -m pip install "swebench==5.0.2"   # Windows
# .venv-harness/bin/python -m pip install "swebench==5.0.2"     # macOS/Linux
```

The grader finds it automatically (or set `SWEBENCH_PYTHON`, or `[harness].python`
in the experiment config). Validate the whole harness path on one dev instance
first — this grades the **gold** patch and must report `PASSED`:

```bash
python scripts/validate_harness.py pylint-dev__astroid-1268
```

On Windows the harness corrupts the LF-only container files, so grading is
routed through `evaluation/_swebench_lf_shim.py` automatically. **Reported runs
execute under Linux**, so prefer the WSL path below; the shim is a fallback.

### Recommended: run under WSL (Linux)

Reported main runs execute on Linux. On Windows, WSL2 provides that environment
and Docker Desktop shares its engine with the distro (same images, no re-pull).

```powershell
wsl --install -d Ubuntu            # one-time, if no distro exists
wsl --set-default Ubuntu
# enable WSL integration for this distro in Docker Desktop (Settings > Resources
# > WSL Integration), or set "IntegratedWslDistros": ["Ubuntu"] in
# %APPDATA%\Docker\settings-store.json while Docker Desktop is stopped, then
# restart Docker Desktop.
wsl -d Ubuntu -- bash /mnt/c/.../scripts/wsl_setup_harness.sh
```

`wsl_setup_harness.sh` installs `uv`, creates a CPython 3.11 harness venv with
`swebench==5.0.2` (default `/root/skills-harness`), and writes
`/etc/profile.d/skills-harness.sh` exporting `SWEBENCH_PYTHON` so the framework
finds it automatically. Then, from Windows:

```powershell
wsl -d Ubuntu -- bash -lc "cd <repo> && PYTHONPATH=src python3 -m skills_experiment grade --experiment pilot"
```

Validate the Linux path first — grading the gold patch must print `PASSED`:

```powershell
wsl -d Ubuntu -- bash -lc "cd <repo> && PYTHONPATH=src python3 scripts/validate_harness.py pylint-dev__astroid-1268"
```


Then the full attempt -> grade -> analyze cycle:

```bash
python -m skills_experiment run   --experiment pilot-dev          # captures patches
python -m skills_experiment grade --experiment pilot-dev          # official harness
python -m skills_experiment analyze --experiment pilot-dev        # stats + effects
```

`run --grade` runs both steps in one go.

---

## Run log

One row per attempt in `runs/<experiment_id>/runs.csv` (+ `runs.jsonl`), matching
the handoff schema. Per-attempt artifacts live under
`runs/<experiment_id>/attempts/<instance>/<condition>/attempt_XX/`:

```text
patch.diff      the candidate patch (what gets graded)
messages.jsonl  the full normalized transcript
condition.json  the exact system prompt / tool list / hashes used
result.json     stop reason, steps, tool errors
```

`grade` fills in `evaluation_status` / `failure_category` / `harness_version` in
place (writing back to `runs.jsonl` and `runs.csv`). It also records per-attempt
test tallies parsed from the harness's per-instance reports:
`tests_passed` / `tests_total`, plus `fail_to_pass_passed` / `fail_to_pass_total`
and `pass_to_pass_passed` / `pass_to_pass_total`. `analyze` writes
`runs/<experiment_id>/analysis.json`. Harness predictions and raw reports are
kept under `runs/<experiment_id>/harness/`.

---

## Status & known limitations

- ✅ Model layer + registry (step 11) — swap models via config.
- ✅ Three conditions with isolation + fairness checks.
- ✅ SWE-bench Lite loading + the 5-task main subset and the 3-task dev subset.
- ✅ Agent loop, tools, sandboxes, run logging, CLI.
- ✅ **Grading** via the official SWE-bench harness (`swebench==5.0.2`), grouped
  per (condition, attempt), with a documented failure-handling + rerun policy.
- ✅ Analysis: resolved rate + task-level bootstrap effects, cost/token/tool
  accounting, and per-attempt tests-passed counts in the run log.
- ✅ **Docker sandbox** validated end to end on a real dev image
  (`python scripts/validate_sandbox.py`): container start, exec, read/write/list,
  and patch capture.
- ⚠️ **`gpt-6-luna` is a fictional placeholder** — set a real `model_id` before any run.
- ⚠️ No provider SDK is installed yet in the agent environment; install the one
  you use (`pip install -e ".[openai]"`, `.[anthropic]`, or `.[google]`) and add
  a key to `.env`. (The OpenAI SDK is installed in the Linux harness venv for
  shakedown runs with `deepseek-flash` / `groq-gpt-oss-120b`.)
- Cost is **not** computed in-repo: run logs record input/output/total tokens only;
  derive dollar cost externally as tokens × the provider's current per-token rate.
- ⚠️ The dataset `revision` is recorded as the configured string (`"main"`), not a
  resolved commit sha — pin/record the sha before the main phase.
- ⚠️ The Anthropic and Gemini adapters are written against their public APIs but
  have **not** been executed against live endpoints. Validate with one call each.
- ⚠️ The `local` sandbox is smoke-only; trustworthy runs need `docker`.

See `PROTOCOL.md` for what is frozen and the remaining open choices.

## Open questions (see handoff §11)

- Which model + exact version is the study's fixed model?
- 20 / 25 / 30 main tasks, and 2 / 3 repeats?
- Random vs. stratified main-phase sampling (this pilot uses one-per-repo).
- Harness version + grading command to pin.
- Is a fourth "pre-loaded skill" condition worth the cost?
