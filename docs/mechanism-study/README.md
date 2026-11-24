# Mechanism / Behavior Study

Branch: `mechanism-study`

Base: `a935024` (Harbor/Pro V2 integration pilot)

Status: **v2 smoke passed; 20-task set frozen; combined 120/120 attempts complete**

## Documents

- `REPLICATION.md` — end-to-end runbook: clone, Harbor/Docker, 60 attempts, extraction, analysis
- `CONTAINER.md` — optional pinned runner image (`docker/replication.Dockerfile` + GHCR)
- `PROTOCOL.md` — research questions, design, endpoints, execution rules
- `DATA_SCHEMA.md` — raw event and derived attempt schema
- `ANALYSIS.md` — paired task-level analysis and plots
- `PILOT_BASELINE.md` — condition-A adherence from the existing pilot logs
- `SMOKE.md` — v2 A/B/C smoke validation
- `CONTENT_AUDIT.md` — optional V3 audit (not used in this run)
- `TASKS.md` — frozen 10-task mechanism set, checksums, image digests
- `TASKS_20.md` — frozen 20-task set, checksums, image digests
- `TASK_SELECTION.md` — selection criteria and 20-task extension plan
- `A_PILOT_PLAN.md` — A-only 20-attempt calibration plan for the 10 candidates
- `../../results/mechanism-pilot-01/RESULTS.md` — completed run results
- `../../results/mechanism-20a-pilot-01/RESULTS.md` — A-only 20-task pilot result (task set not frozen)
- `../../results/mechanism-20-combined/RESULTS.md` — combined 20-task, 120-attempt result
- `../../results/mechanism-20-combined/STATISTICAL_ANALYSIS.md` — task-level statistical section

## Reproduce this study

Three levels. Level 0 is the one to run against any clone of this branch; it
needs no Docker, no network, and no API key.

| Level | What it establishes | Needs | Time |
|---|---|---|---|
| **0 — verify artifacts** | the committed plan, manifests, statistics, prompt text, and frozen task set still agree with each other | Python 3.11+ | ~1 s |
| **1 — re-run the study** | a new draw from the same protocol (60 attempts; the 120-attempt combined set also needs its extension arms) | Docker, Harbor 0.25.0, DeepSeek key, ~40 GB | ~3 h / ~6 h |
| **2 — re-analyse a run** | extraction → manifest → task-level statistics from your own Harbor jobs | Harbor job artifacts | minutes |

### Level 0 — verify what is committed

```bash
python scripts/verify_replication.py             # both runs
python scripts/verify_replication.py --run mechanism-pilot-01 --quiet
```

It re-derives 122 invariants and exits non-zero on the first kind of drift that
matters: a prompt edited after the run, a plan that is not the frozen
randomization, a manifest row that disagrees with its plan row or with the
frozen task checksum/image digest, a published per-condition count that cannot
be recomputed from the manifest, or a protocol anchor (Harbor 0.25.0, Pro commit
`66f9276`, model caps) that changed. It cannot check the model's behavior; that
is what level 1 is for.

This is also the reviewer path. A reviewer needs no Docker, no API key, and no
`harbor` install: the check proves that the committed plan, manifests, and
statistics still agree with each other and with the frozen task set. The numbers
themselves are in `../../results/mechanism-pilot-01/RESULTS.md` and
`../../results/mechanism-20-combined/RESULTS.md`.

`tests/test_replication_artifacts.py` runs the same check under `pytest`, and
`.github/workflows/replication-verify.yml` runs it on every push that touches the
artifacts, the plans, or the prompt text.

### Level 1 — re-run the study

The protocol is the 60-attempt arm from `REPLICATION.md` §1–13: 10 tasks × 3
conditions × 2 repeats, Harbor 0.25.0, local Docker, `deepseek-flash-1017`,
plan seed `20261103`.

**Container path** (pins the toolchain for you; see `CONTAINER.md`):

```bash
export PRO_DIR="$HOME/src/SWE-bench_Pro-os"
cp .env.example .env                              # set DEEPSEEK_API_KEY

PRO_DIR="$PRO_DIR" scripts/run_mechanism_docker.sh \
  --plan data/mechanism-pilot-01/plan.json --pro-dir "$PRO_DIR" --limit 1    # one attempt first
PRO_DIR="$PRO_DIR" scripts/run_mechanism_docker.sh \
  --plan data/mechanism-pilot-01/plan.json --pro-dir "$PRO_DIR" --workers 2  # the 60 attempts
```

**Native path** (what the reference run used): clone the two repositories at the
pinned commits, install Harbor 0.25.0 with `uv`, add the key, then
`python3 scripts/run_mechanism_wsl.py --plan data/mechanism-pilot-01/plan.json
--pro-dir "$PRO_DIR" --workers 2`. Each step, with the exact commands and
versions, is in `REPLICATION.md`:

| Step | Section |
|---|---|
| clone harness + SWE-bench Pro at the pinned commits | §3 |
| install `harbor[modal]==0.25.0` under `uv` | §4 |
| Docker / WSL wiring, pre-pull the 10 task images | §5 |
| credentials | §6 |
| dry-run the 60 commands, then run them | §7–8 |
| monitor, resume, extraction, analysis | §9–12 |

Extraction and analysis are independent of how the run was launched
(`REPLICATION.md` §11–12). Before spending three hours, run the plan's dry-run
(`--dry-run`, prints 60 `harbor run` commands) and then a single attempt
(`--limit 1`); that catches a bad key, a stale Harbor, or an unreachable image
in one trial instead of sixty.

**The 120-attempt combined result is not one command.** It is assembled from the
60-attempt arm plus a 20-attempt A-only pilot plus a 40-attempt B/C extension
across three A screens; the new-task A arm was *not* interleaved with its B/C
arm (`results/mechanism-20-combined/RESULTS.md` says so explicitly). Running
`--plan data/mechanism-20-combined/plan.json` in one pass produces 120 attempts,
but it is a *different* design (A and B/C interleaved, A re-run for the new
tasks) and must be reported as such, not as a replication of the combined
number.

### Level 2 — re-analyse a run you already have

```bash
python scripts/extract_behavior.py \
  --jobs "$PRO_DIR/jobs" \
  --pattern "mechanism-v2-[0-9][0-9]-*" \
  --dataset data/raw/swebench_pro_default.json \
  --out data/derived/mechanism-pilot-01

python scripts/summarize_mechanism_run.py \
  --plan data/mechanism-pilot-01/plan.json \
  --attempts data/derived/mechanism-pilot-01/attempts.json \
  --status data/mechanism-pilot-01/run_status.jsonl \
  --out results/mechanism-pilot-01
```

`--dataset` is only needed for the F2P/P2P fractions (build the index with
`REPLICATION.md` §10). The task-level bootstrap/permutation section is
`scripts/statistical_analysis_mechanism_20.py`.

### What is pinned, and where

| Item | Pin | Recorded in |
|---|---|---|
| Benchmark | SWE-bench Pro V2 @ `66f92766…` | `TASKS_20.md`, `data/mechanism-20-final/tasks.json`, run metadata |
| Task tree | per-task file checksum | `TASKS.md`, `run_manifest.json`, `data/mechanism-20-final/tasks.json` |
| Task environment | per-task image digest (`sha256:…`) | same three files |
| Harbor | `0.25.0`, local Docker | run metadata, `REPLICATION.md` §4 |
| Experimental text | v2 body SHA-256 `586b1376…` | this file, every attempt row |
| Design | 10×3×2 / 20×3×2, plan seed `20261103` (the combined plan mixes its component seeds) | `data/*/plan.json` |
| Model | `deepseek-flash` via `api.deepseek.com`, thinking medium | run metadata |
| Budgets | 80 steps, 1 000 000 tokens, 16 384/response, 3 000 s | run metadata |

### What cannot be pinned

- **Trajectories.** DeepSeek exposes no sampling seed, so a re-run is a new
  stochastic draw. Do not require a new run to match the outcome counts.
- **The model service.** The provider can change the build behind a model id.
  Record the date and model string with any new run.
- **The HuggingFace dataset index.** It only supplies test membership; the task
  tree is pinned by the Pro commit. Record the SHA-256 of the file you build.
- **Wall-clock.** Concurrency, host speed, and image cache change the elapsed
  time, not the design.

`REPLICATION.md` §13 lists the exactness checks that *should* match: 60/60
`rc=0`, zero Harbor exceptions, one workflow hash, C-only skill loading, and
image digests identical to `TASKS.md`.

## Instrumentation

- `src/skills_experiment/observability.py` — JSONL event recorder
- `src/skills_experiment/agent/loop.py` — emits `run_start`, `model_call`, `run_end`
- `src/skills_experiment/agent/tools.py` — emits per-tool duration, exit code,
  output size/hash, and sanitized arguments
- `src/skills_experiment/harbor_agent.py` — uses v2 by default, writes
  `events.jsonl` and richer `context.metadata`
- `src/skills_experiment/behavior.py` — extracts attempt/event tables
- `scripts/extract_behavior.py` — CLI for Harbor jobs

## Workflow version

The mechanism run uses the canonical v2 workflow:

`src/skills_experiment/assets/prompts/workflow_instructions_v2.md`

Body SHA-256:
`586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`

B and C use the same v2 body; C must load it through `load_skill`.

V3 remains an optional, unaudited future arm and is not part of this run.

## Completed gates

1. A/B/C v2 smoke passed.
2. `events.jsonl`, skill loading, and extractor output verified.
3. Image digests and task checksums recorded in `TASKS.md`.
4. Randomized 60-attempt order generated and recorded.
5. 60/60 attempts completed with zero exceptions; results in
   `results/mechanism-pilot-01/RESULTS.md`.
6. 20-task set frozen 2026-11-14 in `TASKS_20.md`.
7. 120/120 combined attempts complete; results in
   `results/mechanism-20-combined/RESULTS.md`.
