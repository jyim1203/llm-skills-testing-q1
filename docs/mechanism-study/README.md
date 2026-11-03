# Mechanism / Behavior Study

Branch: `mechanism-study`

Base: `a935024` (Harbor/Pro V2 integration pilot)

Status: **v2 smoke passed; 60-attempt run in progress**

## Documents

- `PROTOCOL.md` — research questions, design, endpoints, execution rules
- `DATA_SCHEMA.md` — raw event and derived attempt schema
- `ANALYSIS.md` — paired task-level analysis and plots
- `PILOT_BASELINE.md` — condition-A adherence from the existing pilot logs
- `SMOKE.md` — v2 A/B/C smoke validation
- `CONTENT_AUDIT.md` — optional V3 audit (not used in this run)
- `TASKS.md` — frozen 10-task mechanism set

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

## Quick extraction

```bash
python scripts/extract_behavior.py \
  --jobs /path/to/Harbor/jobs \
  --dataset data/raw/swebench_pro_default.json \
  --out data/derived/mechanism-pilot-01
```

This writes `attempts.csv`, `events.csv`, and `attempts.json`.

## Next gates before the 60

1. Finish the A/B/C v2 smoke.
2. Verify `events.jsonl`, skill loading, and extractor output.
3. Record image digests/checksums.
4. Generate the randomized 60-attempt order.
5. Run the 60.
