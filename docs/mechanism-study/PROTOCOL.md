# Mechanism / Behavior Study Protocol

**Status:** completed 2026-11-04, branch `mechanism-study`<br>
**Base:** `a935024` (Harbor/Pro V2 integration pilot)<br>
**Experiment ID:** `mechanism-pilot-01`<br>
**Run:** 60/60 attempts completed; see `results/mechanism-pilot-01/RESULTS.md`.

## 1. Motivation

The binary pilot showed task-level separation, not condition separation:

| Task | A | B | C |
|---|---|---|---|
| Ansible hard | resolved | resolved | resolved |
| OpenLibrary hard | unresolved | unresolved | unresolved |
| qutebrowser hard | resolved | resolved | resolved |

With 3 tasks and 1 repeat, that design has no useful power for a resolve-rate claim. The revised study asks a different question: **does the delivery mechanism of procedural guidance change how the agent works, and at what cost?**

A/B/C still use identical workflow content. B injects it into the system prompt; C packages it as a skill that must be loaded. A receives no workflow text. This isolates delivery (C vs B) and content (B/C vs A).

## 2. Research questions

| ID | Question | Contrast | Role |
|---|---|---|---|
| RQ1 | Does skill delivery change process behavior? | C vs B | Primary |
| RQ2 | Does workflow content change process behavior? | B/C vs A | Secondary |
| RQ3 | Does delivery change efficiency? | C vs B | Secondary |
| RQ4 | Does delivery change outcomes? | C vs B | Exploratory |
| RQ5 | Where in the trajectory do differences emerge? | All | Qualitative |

## 3. Conditions and manipulation

| Condition | System prompt | Workflow text | `load_skill` |
|---|---|---|---|
| A baseline | base prompt | none | no |
| B prompt | base prompt + full workflow | inline | no |
| C skill | base prompt + skill metadata + require-load instruction | in `SKILL.md` | yes |

All three use the same tool set except for `load_skill`, which only C exposes.

### Workflow version

The mechanism study uses the canonical v2 workflow:

- body SHA-256: `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`
- source: `src/skills_experiment/assets/prompts/workflow_instructions_v2.md`

B and C must use the same v2 body; the adapter records both hashes.

`workflow_instructions_v3.md` remains in the branch as an optional future arm.
It is **not** part of this run, and the study makes no claim that v3 is stronger.
The pilot baseline already suggests the canonical workflow is largely generic:
A ran a post-edit test in 3/3 tasks, a pre-edit test in 0/3, and read/searched
before editing in 2/3. That is recorded as a limitation, not a reason to add an
unaudited second content arm.

### Content audit

The V3 audit is **optional and deferred**. If v3 is ever used, classify each
instruction as generic prior, Python-repository-specific, or non-obvious before
running it. Do not add v3 to the 60-attempt mechanism run.

## 4. Design

| Item | Value |
|---|---|
| Tasks | 10 |
| Conditions | A, B, C |
| Repeats | 2 per task-condition |
| Attempts | 10 × 3 × 2 = 60 |
| Execution | randomized per-attempt order, 2 concurrent Harbor workers |
| Task order | interleaved across conditions and repeats |
| Model | `deepseek-flash-1017` |
| Thinking | enabled, medium effort |
| Response cap | 16,384 tokens |
| Cumulative cap | 1,000,000 tokens |
| Step cap | 80 |
| Time cap | 3,000 s |
| Agent | `skills_experiment.harbor_agent:HarborSkillsAgent` |
| Verifier | Pro V2 task verifier; record shared vs patch-replay mode |

Interleaving means: generate all 60 `(task, condition, repeat)` tuples, shuffle
them with a recorded seed, and launch one trial per Harbor job. Do not run all
of A, then all of B, then all of C.

### Task strata

The final task list is frozen in `TASKS.md` before any mechanism run.

- 2 known ceiling: Ansible `e9e600`, qutebrowser `3e21c8`
- 2 known floor / budget-limited: OpenLibrary `0dc5b2` plus one similar
- 6 new tasks across `ansible/ansible`, `internetarchive/openlibrary`, and
  `qutebrowser/qutebrowser`

Selection uses only condition-A pilot outcomes and static task properties
(repo, patch size, test count, `hard`). Do not select tasks on B/C outcomes.
Pro V2 has only three Python repositories, so multiple tasks per repo are
allowed.

**No formal 20–80% calibration phase.** The pilot anchors and static
stratification are enough for a behavior study. If a quick screen is desired,
run A only on 8–10 candidates with 1 repeat and use it only for strata; it is
not a separate experiment and must not be used to select on B/C outcomes.

## 5. Endpoints

### Primary

| ID | Endpoint | Type | Definition |
|---|---|---|---|
| P1 | Test-before-edit rate | binary | At least one test command before the first edit |
| P2 | Read/search-before-edit rate | binary | At least one read/search/list before the first edit |
| P3 | Time to first edit | continuous | Seconds from `run_start` to first edit; fallback: first-edit event index |
| P4 | Total tokens per attempt | continuous | Input + output tokens from the provider usage record |

P1/P2 are workflow-adherence behavior; P3 is pacing; P4 is efficiency. P1 and
P3/P4 are available from the new event log; P1/P2 also work from messages.

**Post-edit verification is deliberately not primary:** condition A already
verified after its last edit in all 3 pilot tasks (see `PILOT_BASELINE.md`). It
is retained as a secondary/treatment-check endpoint so a ceiling can be
documented rather than mistaken for a treatment effect.

### Secondary

- **post-edit verification rate** (expected ceiling; report explicitly)
- number of test commands, test-to-edit ratio, verification intensity
- tool-call mix (`run_shell`, `read_file`, `write_file`, `list_dir`, `load_skill`)
- unique files read/edited, patch files/lines, repeated commands
- tool errors, unknown tool calls, budget exhaustion
- wall time, model latency, tool duration
- resolved, reward, fail-to-pass fraction, pass-to-pass fraction
- tokens per resolved task, steps per resolved task

Outcome is secondary/exploratory. Do not describe a resolve-rate difference as
causal with 10 tasks.

## 6. Data collection

See `DATA_SCHEMA.md`.

Per attempt, persist:

- `agent/messages.jsonl` — full transcript, including `reasoning_content`
- `agent/events.jsonl` — event stream: `run_start`, `model_call`, `tool_call`,
  `run_end`, with timestamps, per-call usage, durations, and tool metadata
- `agent/patch.diff` — captured patch
- `verifier/output.json` — test statuses
- trial `result.json` / `config.json` — Harbor provenance, condition, repeat
- `attempts.csv` — one derived row per attempt
- `events.csv` — one derived row per tool event

`scripts/extract_behavior.py` builds the derived tables from Harbor job
directories.

## 7. Analysis

See `ANALYSIS.md`. Summary:

- Unit: task. Average the 2 repeats per task-condition, then compare tasks.
- Contrasts: C−B (delivery), B−A and C−A (content).
- Binary endpoints: paired task-level differences, sign test, bootstrap CI.
- Continuous endpoints: paired task-level differences with bootstrap CI;
  report median and mean; effect size.
- Stratify by ceiling/floor/intermediate; do not pool blindly.
- Optional mixed model: `metric ~ condition + stratum + (1 | task)`; label as
  descriptive.
- Plot per-task dumbbells, token distributions, tool-mix bars, and tool-transition
  counts.
- Qualitatively code 2–3 traces per condition for failure modes and adherence.

No p-hacking. P1–P4 are the primary family; everything else is exploratory.

## 8. Censoring and exclusions

- Infrastructure error, API failure, or verifier failure: excluded from primary
  endpoints and reported separately.
- `token_budget` and `elapsed_budget`: **not** ordinary failures. Keep the
  attempt; report budget exhaustion separately. For outcome, report
  “resolved within budget.”
- Empty patch is a valid behavioral observation; do not drop it.
- Skill-load failure in C is a treatment failure; record it.

## 9. Provenance

Record per attempt:

- harness git commit, Pro repo commit, Harbor version
- model ID and API model string
- task ID, image digest, task checksum
- condition, repeat, job/trial ID
- workflow version/hash, system-prompt hash, task-prompt hash
- verifier mode, network mode, CPU/memory, concurrency
- timestamps and wall time

Do not log API keys. Store raw reasoning locally; keep it out of any public
artifact unless reviewed.

## 10. Pre-registration checklist

- [x] Freeze task IDs and strata in `TASKS.md`
- [x] Freeze v2 workflow body and hash
- [x] Confirm B/C use identical v2 body
- [x] A-adherence audit complete; V3 content audit deferred and unused
- [x] Validate event logging on one non-scored attempt
- [x] Validate F2P parser on one known pass and one known fail
- [x] Generate and record the randomized 60-attempt order
- [x] Record verifier mode and image digests
- [x] Start and complete the 60-attempt run

## 11. Known risks

- V2 is largely generic prior; the study may find no behavioral effect.
- Ceiling/floor tasks may dominate variance; stratification is essential.
- Tool logs are coarse; shell edit detection is heuristic.
- No sampling seed; repeats are stochastic but not guaranteed independent.
- The 1M cap censors hard tasks.
- Shared verifier is weaker than fresh-sandbox patch replay.
- Ten tasks support description, not a precise causal claim.
