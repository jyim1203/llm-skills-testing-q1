# Mechanism / Behavior Study

Draft branch: `mechanism-study`  
Base: `a935024` (Harbor/Pro V2 integration pilot)  
Status: **design and instrumentation only; no runs launched**

## Documents

- `PROTOCOL.md` — research questions, design, endpoints, execution rules
- `DATA_SCHEMA.md` — raw event and derived attempt schema
- `ANALYSIS.md` — paired task-level analysis and plots
- `PILOT_BASELINE.md` — condition-A adherence from the existing pilot logs
- `CONTENT_AUDIT.md` — V3 novelty audit to fill before the run
- `TASKS.md` — task strata and freeze checklist (task list not yet frozen)

## Instrumentation

- `src/skills_experiment/observability.py` — JSONL event recorder
- `src/skills_experiment/agent/loop.py` — emits `run_start`, `model_call`, `run_end`
- `src/skills_experiment/agent/tools.py` — emits per-tool duration, exit code,
  output size/hash, and sanitized arguments
- `src/skills_experiment/harbor_agent.py` — uses V3 skill, writes `events.jsonl`
  and richer `context.metadata`
- `src/skills_experiment/behavior.py` — extracts attempt/event tables
- `scripts/extract_behavior.py` — CLI for Harbor jobs

## Stronger skill

`src/skills_experiment/assets/prompts/workflow_instructions_v3.md`

Body SHA-256:
`82d69b9866b0e1ffc81de94849d737e3bec0e362156710ba2dac394e4dca75d1`

B and C use the same V3 body; C must load it through `load_skill`.

## Quick extraction

```bash
python scripts/extract_behavior.py \
  --jobs /path/to/Harbor/jobs \
  --dataset data/raw/swebench_pro_default.json \
  --out data/derived/mechanism-pilot-01
```

This writes `attempts.csv`, `events.csv`, and `attempts.json`.

## Next gates before execution

1. Content audit + A-adherence audit.
2. Freeze 10 tasks and image digests.
3. Validate event logging on one non-scored attempt.
4. Validate F2P parser.
5. Record randomized order.
