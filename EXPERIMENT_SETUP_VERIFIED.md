# SWE-bench Verified Experiment Setup - DeepSeek V4.1 Flash 1017

**Status:** setup implemented; do not launch the 240-attempt run until the
30-attempt pilot, image lock, and live API checks pass.

**Date:** 2026-11-02

## 1. Research question

Estimate the effect of three instruction-delivery conditions on an agent's
ability to resolve SWE-bench Verified issues:

- **A - baseline:** base system prompt + task, no workflow text or skill.
- **B - prompt instructions:** the workflow text injected directly into the
  system prompt.
- **C - skill:** the same workflow body packaged as a `SKILL.md`, with only
  name/description advertised and the body loaded through `load_skill`.

The primary contrast is **C vs B** (skill packaging vs direct prompt). B vs A
and C vs A are secondary. The scope is the 10 tasks below, not the Verified
population.

## 2. Design

| Item | Value |
|---|---|
| Tasks | 10 instances, one per repository |
| Conditions | A, B, C |
| Repeats | 8 per task x condition in the main run |
| Attempts | 3 x 10 x 8 = **240** |
| Pilot | 3 x 10 x 1 = **30** attempts |
| Difficulty strata | 2 easy, 3 medium, 5 hard; one hard task is from the `>4 hours` bucket |
| Order | repeat-major; randomized task order per repeat; randomized condition order within each task x repeat |
| Parallelism | **2 Docker workers** |
| Model | DeepSeek V4.1 Flash 1017 via the OpenAI-compatible API |
| Decoding | thinking enabled; `reasoning_effort=medium`; 16,384 per response; 1,000,000 cumulative |
| Design seed | 20261015 (plan order only; the API has no sampling seed) |
| Sandbox | one fresh Docker container per attempt, per-task SWE-bench image |
| Grading | official `swebench==5.0.2` harness in the WSL venv |

Run configs:

- `configs/experiments/verified-pilot.toml` - 30 attempts, `repeats = 1`
- `configs/experiments/verified-main.toml` - 240 attempts, `repeats = 8`
- `data/task_selection_verified.json` - frozen task list
- dataset revision: `78f471bf655a3137b2e8a75af1501690ec009ec3`

## 3. Tasks and selection rationale

The set is **purposive and hard-weighted**, not a probability sample of
Verified:

- source: `SWE-bench_Verified`, test split, pinned revision;
- one instance per repository to avoid repository-level dominance;
- no overlap with the previous Lite task IDs;
- hard stratum over-sampled relative to the Verified base rate (9% hard);
- exactly one `>4 hours` task as a stress case;
- clear issue text, reproducible failing tests, and moderate P2P suites.

| Tier | Instance | Focus | Gold patch | F2P / P2P |
|---|---|---|---|---:|
| Easy | `pallets__flask-5014` | Empty Blueprint name must raise `ValueError` | +3/-0, 1 file | 1 / 59 |
| Easy | `psf__requests-5414` | Invalid IDNA host should raise `InvalidURL`, not `UnicodeError` | +1/-1, 1 file | 1 / 130 |
| Medium | `astropy__astropy-13033` | `TimeSeries` error message must name required columns | +11/-3, 1 file | 1 / 20 |
| Medium | `mwaskom__seaborn-3187` | Legend labels must preserve `ScalarFormatter` offset | +12/-0, 2 files | 2 / 248 |
| Medium | `scikit-learn__scikit-learn-12973` | `LassoLarsIC.fit(copy_X=...)` should not override constructor value | +7/-3, 1 file | 1 / 32 |
| Hard | `django__django-15957` | `Prefetch()` with a sliced queryset | +26/-7, 1 file | 4 / 89 |
| Hard | `sympy__sympy-14248` | `MatrixSymbol` subtraction printing | +56/-9, 3 files | 2 / 433 |
| Hard | `pytest-dev__pytest-6197` | Do not collect arbitrary `__init__.py` files | +6/-18, 1 file | 2 / 145 |
| Hard | `pylint-dev__pylint-8898` | `bad-names-rgxs` must not split regex commas | +30/-2, 3 files | 1 / 18 |
| Hard, **>4h** | `sphinx-doc__sphinx-7590` | Large multi-file Sphinx build fix; stress case | +89/-18, 3 files | 1 / 24 |

The other two `>4h` tasks were excluded because `xarray-6992` has 945 P2P tests
and `sympy-13878` would duplicate SymPy and has a 142-line patch.

## 4. Conditions

| | A | B | C |
|---|---|---|---|
| Base system prompt | same | same | same |
| Task prompt | same | same | same |
| Workflow body | absent | full text in system prompt | same body in `SKILL.md` |
| Skill metadata | none | none | name + description in system prompt |
| `load_skill` tool | no | no | yes |
| Body availability | - | turn 1 | after tool call |
| Extra call | none | none | one required load call |

The fairness check confirms that B's workflow body and C's skill body hash
identically. C must load the skill in 100% of attempts; A/B must have zero
`load_skill` calls.

Current B/C body hash:
`586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`.

## 5. Parameters and justifications

| Parameter | Value | Why | What to report |
|---|---:|---|---|
| Thinking mode | enabled | Requested for the main run; DeepSeek returns `reasoning_content` and requires it to be passed back on tool-calling turns. | Thinking toggle; reasoning-token counts. |
| Reasoning effort | `medium` (maps to `high`) | Requested "medium"; DeepSeek accepts `medium` for compatibility and maps it to `high`. | Requested value and provider mapping. |
| Temperature | 0.2 | Recorded for provenance. **DeepSeek ignores temperature in thinking mode.** | Duplicate-trajectory check. |
| Top-p | 1.0 | Only `0.95-1.0` is effective for `deepseek-flash` in thinking mode. | Effective request value. |
| Per-response cap | 16,384 tokens | Caps one assistant completion (including reasoning), not the attempt. | `stop_reason=length`; truncated tool calls. |
| Cumulative token cap | 1,000,000 tokens | Cumulative input + output per attempt; bounds time and cost. | Actual tokens; `token_budget` stops. |
| Max steps | 80 | One step = one model completion, not one tool call. | `max_steps` stops; mean steps. |
| Time cap | 1,800 s | Per-attempt wall-clock safety. | `elapsed_budget` stops; maximum attempt time. |
| Tool timeout | 120 s | Bounds one shell/test command. | Tool errors/timeouts. |
| Repeats | 8 | Per-task rate granularity 0.125; task-level analysis. | Per-task 8-run rates. |
| Design seed | 20261015 | Reproducible task/condition order only. | `run_order`; `plan.json`. |
| Sampling seed | none | DeepSeek Chat Completions exposes no `seed` parameter. | Explicitly record "unsupported". |
| Parallelism | 2 workers | Safer on 16 GB; each worker has its own container, workspace, and model client. | Worker start/end times; memory peaks. |

**Budget semantics:** `max_tokens` is a cumulative per-attempt budget (input +
output), checked after each step, so it can overshoot by one response. The
16,384 limit is per model response.

## 6. Execution order and concurrency

The concurrency implementation is in `src/skills_experiment/runner.py`:

1. `build_plan()` uses `random.Random(config.seed)`.
2. For each repeat, it shuffles the task order.
3. Within each task x repeat, it includes exactly one A, B, and C, with a
   shuffled condition order.
4. It writes the full plan to `runs/<experiment>/plan.json`.
5. `run_plan()` uses `ThreadPoolExecutor` with `workers = 2`.
6. Each worker gets its own `OpenAIChatClient`; Docker containers and
   workspaces remain per-attempt and isolated.
7. `RunLogger.append` is lock-protected so JSONL/CSV rows cannot interleave.
8. A worker exception is recorded as an infrastructure-error row rather than
   silently dropping the attempt.

Pure random condition assignment is **not** used: it can leave task x
condition cells unbalanced. The plan is constrained to one of each condition
per task x repeat, then randomized.

## 7. Memory: 2 workers on ~16 GB

Two workers is the chosen configuration and is the right default for 16 GB.
Typical use should fit; spikes near the upper end of the table need monitoring.

| Component | Estimated memory |
|---|---:|
| Docker Desktop / WSL 2 overhead | 2-4 GB |
| OS, editor, browser | 3-4 GB |
| 2 x SWE-bench Python containers | 3-6 GB |
| Test/collection spikes | 1-3 GB |
| **Typical total** | **9-17 GB** |

Docker Desktop currently reports a 15.2 GiB VM, so **3 workers is not the
default** even though the host has 32 GB. On this allocation, monitor
`docker stats` during the pilot and keep the worker count at 2 unless every
container stays below ~2 GB. Do not add hard `--memory` limits until measured;
an OOM-killed test becomes an infrastructure error.

## 8. Before launching the pilot

Completed:

- [x] Freeze `data/task_selection_verified.json` with the 10 IDs.
- [x] Pin the `SWE-bench_Verified` dataset revision and cache the 10 instances.
- [x] Create `verified-pilot.toml` and `verified-main.toml`.
- [x] Set `deepseek-flash-1017` to thinking enabled, effort medium, 16,384 per
      response, timeout 600, retries 3.
- [x] Implement seeded repeat-major planning and two-worker execution.
- [x] Add tests for plan balance, plan reproducibility, parallel logging, and
      the DeepSeek thinking payload/reasoning round-trip.
- [x] Live API smoke on Windows and in WSL: auth works; thinking returns
      `reasoning_content`; a tool-calling turn followed by a tool result
      succeeds with reasoning content passed back.
- [x] WSL harness venv exists at `/root/skills-harness` with
      `swebench==5.0.2` and `openai`.
- [x] Docker Desktop is running: Windows and Ubuntu WSL can both see the
      Docker server; the VM reports 15.2 GiB / 16 CPUs.
- [x] WSL integration for Ubuntu is working.
- [x] Harness gold-patch validation passed for `pylint-dev__astroid-1268`
      (`swebench==5.0.2`, resolved).

Still required:

- [ ] Commit the setup changes before running. The worktree is currently dirty
      and `framework_git_commit` would still record the old HEAD (`193db2e`).
- [ ] Pull all ten task images and run
      `preflight --experiment verified-pilot --write-lock`.
- [ ] Run the **30-attempt pilot**: 10 tasks x 3 conditions x 1 repeat.
- [ ] Measure wall time, RAM, stop reasons, image failures, and C's skill-load
      rate.
- [ ] Confirm `sphinx-7590` is usable as the `>4h` stress task.
- [ ] Check that `stop_reason=length` is not dominated by reasoning tokens.
- [ ] Freeze the analysis plan before looking at outcomes.

Pilot command (WSL; the harness venv has both `openai` and `swebench`):

```bash
cd "/mnt/c/Users/Jonat/UCSD/2026-2027/DSC 180A/Skills Test Q1"
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment plan --experiment verified-pilot
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment preflight --experiment verified-pilot --write-lock
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment run --experiment verified-pilot --resume --grade
```

The Windows Python has `openai` for a plan-only check, but `--grade` should be
run under WSL so `resolve_harness_python()` finds the harness venv.

## 9. Analysis plan

- **Unit:** task x condition; attempts are repeated measures nested within task.
- **Primary:** paired task-level C vs B effect; bootstrap over the 10 tasks or
  a hierarchical logistic model with a task random intercept.
- **Secondary:** B vs A, C vs A, and difficulty-stratum descriptions.
- **Do not** treat 240 attempts as 240 independent observations. The task-level
  sample is 10, with 2/3/5 per stratum.
- Report all attempts under intention-to-treat. Report `max_steps`,
  `token_budget`, `length`, and `elapsed_budget` stops by condition; do not
  silently drop them.
- Exclude only pre-specified infrastructure errors from the primary estimate;
  show them separately.
- Report per-task 8-run rates alongside aggregate estimates.
- Use `evaluation_status`, not the null `resolved` field.
- State the contamination limitation: Verified is public; absolute rates are
  not clean generalization estimates.

## 10. Known limitations

- Purposive one-per-repo sample; not representative of Verified prevalence.
- Ten of twelve repositories represented; hard over-sampled.
- 10 task-level units still give wide confidence intervals, especially within
  the 3-task strata.
- Public benchmark contamination cannot be ruled out.
- DeepSeek thinking mode ignores temperature and the API has no sampling seed.
  Eight repeats are therefore **not guaranteed to be independent**; the
  one-repeat pilot cannot estimate between-repeat variance.
- Budget caps can bind, especially on the `>4h` task; cap-bound outcomes are
  part of the result.
- Two workers is a memory trade-off; throughput will be lower than three.
