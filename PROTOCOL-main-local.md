# Protocol: main local experiment (`main-local-01`)

Status: **pre-registered before the first `main-local-01` attempt.** The
18-attempt `main-local-pilot-01` run is validation only and is not pooled with
the reported sample.

`PROTOCOL.md` remains the frozen protocol for the DeepSeek setup run
(`pilot-01`); this document covers the local-model study that replaces it as
the main experiment.

---

## 1. Question

> When the substantive workflow text is identical, does delivering it as an
> agent *Skill* (C) improve a local 9B model's SWE-bench Lite performance
> relative to pasting it into the prompt (B), or a bare baseline (A)?

Primary contrast: **C (skill) vs B (direct prompt)**. A anchors both.

## 2. Why a separate local experiment

`pilot-01` (DeepSeek V4.1 Flash) validated the pipeline end to end but hit a
ceiling: A 15/15, B 14/15, C 15/15. With almost no failures, A/B/C cannot
separate. The main study therefore uses a local Qwen 3.5 9B, where the task is
harder and the skill has room to matter. `pilot-01` stays frozen and is
reported only as setup validation.

## 3. Conditions

| Condition | Implementation | What varies |
|---|---|---|
| `A_baseline` | `conditions/baseline.py` | nothing beyond the task |
| `B_prompt_instructions` | `conditions/prompt_instructions.py` | v2 workflow pasted into the system prompt |
| `C_skill` | `conditions/skill.py` | same v2 text packaged as `SKILL.md`, advertised by name/description, loaded on demand |

All three use `base_system_prompt_minimal.md`, which states only the role and
the test-integrity rule; it contains no procedure.

B and C share `workflow_instructions_v2.md`. The runner refuses to start unless
the stripped B prompt body and C skill body are byte-identical. Current fairness
hash: `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`.

C sets `require_load = true`: the agent must call `load_skill` before editing.
This is a deliberate local-model adaptation; the previous 9B smoke never loaded
the skill on its own. A and B never receive a skills directory or the
`load_skill` tool.

Everything else (tool set, budgets, stop conditions, loop) is shared.

## 4. Model under test

* Profile: `configs/models/local-qwen-sampling.toml`.
* Base model: Qwen 3.5 9B, Q4_K_M, served by Ollama 0.40.10 as
  `qwen3.5-9b-agent-64k`.
* Context: 65,536 tokens, q8_0 KV cache, flash attention on, `num_parallel 1`,
  100% GPU on a 12 GB RTX 5070.
* Decoding: **temperature 0.2**, `max_tokens = 16384` per response, SDK timeout
  600 s, 3 retries.

Temperature 0.2 is intentional. At temperature 0 the 9B is deterministic or
near-deterministic, so five repeats would be five copies of one trajectory. The
main run needs independent samples to estimate within-task variance. The
deterministic `local-qwen` profile remains available for smoke tests.

## 5. Tasks

Six tasks, frozen in `data/task_selection_local.json` (Lite `test` split):

| Instance | Repo | Topic |
|---|---|---|
| `django__django-11099` | django/django | web framework / input validation |
| `psf__requests-3362` | psf/requests | HTTP client / decoding |
| `matplotlib__matplotlib-22835` | matplotlib/matplotlib | plotting / color norms |
| `sympy__sympy-20590` | sympy/sympy | symbolic math / object model |
| `scikit-learn__scikit-learn-10297` | scikit-learn/scikit-learn | ML estimator API |
| `pytest-dev__pytest-5495` | pytest-dev/pytest | test framework / assertion rewriting |

The first five are the frozen `pilot-01` main set. The sixth was added **before
any `main-local-01` attempt** as a pre-registered medium-proxy task: one source
file, 25 changed lines, 2 FAIL_TO_PASS and 86 PASS_TO_PASS tests. It adds a
testing-tooling domain and reduces the ceiling without changing the five
already-frozen tasks.

Dataset revision: `b0dde1093fe417d83b7184254edf8199c1f0dff5`. Gold patches and
test patches are eval-only and never exposed to the agent.

## 6. Design and budgets

* 6 tasks x 3 conditions x **5 repeats** = **90 attempts**.
* Interleaved condition order per task; fixed seed `20261015`.
* Budgets: `max_steps = 80`, `max_tokens = 2500000` cumulative,
  `elapsed_seconds = 1800`, `tool_timeout_seconds = 120`.
* Identical budgets across conditions.

Five repeats give a per-task resolved count out of 5 and a within-task variance
estimate. The 9B is verbose and loop-prone; the step/token limits cap runaway
loops. Token-budget stops are recorded and reported as a secondary outcome, not
silently dropped.

Five repeats is an overnight-budget compromise: per-task rates are coarse
(0, 0.2, ..., 1.0) and the task-level CI will be wide. A null result means
"not detectable at this sample size," not "no effect."

**Budget calibration.** The completed 18-attempt pilot ran at 1,500,000
cumulative tokens and 8,192 per response. It stopped 10/18 attempts on the
cumulative budget and 3/18 on the per-response length cap, so the token cap was
binding before the 80-step cap. The main run therefore uses 2,500,000 cumulative
and 16,384 per response. This lets the step cap bind for most attempts while
still bounding runaway loops. The pilot is not re-run and is not pooled; its
budget-bound attempts are the reason for the change.

## 7. Isolation and environments

* Fresh workspace and conversation per attempt.
* One Docker container per attempt, removed on cleanup.
* Image lock: `data/image_locks/main-local-01.json`; the run refuses to start if
  any `:latest` tag resolves to a different digest.
* Dataset bytes are committed under `data/instances/`; every run writes
  `dataset_manifest.json` and records the dataset hash, revision, image digest,
  RNG seed, UTC start time, and framework git commit on every row.
* Reported runs execute under Linux/WSL with the official harness.
* `run --resume` skips attempts already present in `runs.jsonl`; it never
  overwrites completed rows. An attempt interrupted before its row is written
  is simply run again.

## 8. Grading and failure handling

Official SWE-bench harness (`swebench==5.0.2`), never a reimplementation.
Each attempt ends in one status:

| status | meaning | counted? | rerun? |
|---|---|---|---|
| `resolved` | patch passed the tests | yes (numerator) | no |
| `unresolved` | graded and failed (agent-attributable) | yes (denominator) | no |
| `infrastructure_error` | setup/model/harness failure | no | yes, at most once |
| `not_evaluated` | patch produced, not graded yet | no | n/a |

Empty patches and patch-apply failures are agent failures (`unresolved`).
Image pulls, container/apply crashes, and test timeouts are infrastructure
errors. Reruns append a new attempt row; resolved/unresolved attempts are never
rerun. Attempts that already produced a patch are re-graded rather than re-run.

## 9. Metrics and analysis

Primary: **resolved rate** over counted attempts, per condition.

Secondary: input/output tokens, tool calls, steps, elapsed seconds, tests
passed / total, stop reasons, and — for C — skill discovery/load rate.

Analysis plan:

1. Per-task table: resolved count out of 5 for each condition.
2. Aggregate resolved rate per condition with a task-level bootstrap 95% CI
   (the task, not the attempt, is the resampling unit; n = 6). The denominator is
   30 counted attempts per condition unless infrastructure errors remain.
3. Pairwise task-level differences: A vs B, A vs C, B vs C, with bootstrap CIs.
4. Report all attempts, including failures and token-budget stops. Do not
   condition on producing a patch.
5. With only six tasks, the CIs will be wide. Claims are scoped to these six
   tasks, not to SWE-bench Lite as a population.

Interpretation rule, fixed in advance:

* C vs B CI excludes 0 in favor of C -> evidence that skill packaging helps.
* C vs B CI includes 0 -> no detectable difference at this sample size.
* C vs B CI excludes 0 in favor of B -> evidence that skill packaging hurts.

## 10. Deviations from `pilot-01`

| Dimension | `pilot-01` (frozen) | `main-local-01` |
|---|---|---|
| Model | DeepSeek V4.1 Flash | Qwen 3.5 9B (local) |
| Temperature | 0 | 0.2 |
| Base prompt | `base_system_prompt.md` | `base_system_prompt_minimal.md` |
| Workflow | `workflow_instructions.md` | `workflow_instructions_v2.md` |
| Skill load | optional | required (`require_load = true`) |
| Repeats | 3 | 5 |
| Tasks | 5 | 6 (adds pytest-5495) |
| Budgets | 60 steps / 600k tokens | 80 steps / 2.5M tokens; 16k per response |

`pilot-01` is not re-run or pooled with the local study.

## 11. Freezing and provenance

SHA-256 of the frozen inputs (lowercase):

| File | SHA-256 |
|---|---|
| `assets/prompts/base_system_prompt_minimal.md` | `1d3d8d624f0077c0321fa4f856971787eb71a37a9388a1a0b0c9b09c79cfe84b` |
| `assets/prompts/workflow_instructions_v2.md` | `d130ac89aedb06475dda023cd3368b86fac2f49322454ce535647d3e7b1c2293` |
| `data/task_selection_local.json` | `953f8ff0d1dfb8d27add1887eb3b120c113e9eb05febe2cd8b3859678a8e9cbc` |
| `configs/experiments/main-local.toml` | `ba673154393cc05c16e8d6c0bab1551a3dfe9f51e108e44ad7c092a4c98a0db8` |
| `configs/models/local-qwen-sampling.toml` | `1cba867946cc50edba439feb30cde67d569a638f9055e78d81302f5ebf9ba514` |
| `data/image_locks/main-local-01.json` | `558b8ec822c8e6771689b4f1cf364176020cde225c1e9bf5d98d2aebee85b0c9` |

B/C fairness hash: `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`.

The framework git commit at run start is recorded on every row. Changing any
frozen input after the first `main-local-01` attempt is a protocol deviation and
must be reported with the results.

## 12. Stopping and decision rules

* Run all 90 attempts. No optional stopping based on interim results.
* If infrastructure errors remain after one rerun, report them and the counted
  denominator explicitly.
* Do not add or remove tasks, change prompts, or change the model after seeing
  main-run outcomes. A bug fix discovered during the pilot is allowed only
  before the first main attempt, and the change is documented in the commit
  history.

## 13. Pilot

The completed `main-local-pilot-01` used the same six tasks, conditions,
prompts, model profile, and image lock, with **one repeat** (18 attempts) at the
earlier 1,500,000/8,192 budgets. It validated the new pytest image, the tightened
v2 workflow, `require_load`, and grading: 18/18 completed, 0 infrastructure
errors, 10/18 resolved, C loaded the skill 6/6. Its results are not pooled with
the main run. The pilot's 10/18 token-budget stops and 3/18 length stops are what
motivated the main run's 2,500,000/16,384 budgets; the pilot itself is not
re-run. If a future pilot exposes a bug, fix it, document the change, and
re-freeze this protocol before the main run.
