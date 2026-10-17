# Results — pilot-01 (main run)

**Question.** Does packaging a software-engineering procedure as an *on-demand
skill* (Condition C) change agent behavior relative to delivering the same
procedure as *prompt text* (Condition B), or to a plain baseline (Condition A)?

**Run.** 2026-10-16T23:13:58Z → 2026-10-17T00:39:52Z (85.9 min wall-clock).

| | |
|---|---|
| Model | `deepseek-flash` (OpenAI-compatible) |
| Framework commit | `1985e70` |
| Harness | `swebench 5.0.2` |
| Dataset | `SWE-bench/SWE-bench_Lite@b0dde1093fe417d83b7184254edf8199c1f0dff5` |
| Task set | 5 instances, one per repo; manifest `0f1b68ad…` |
| Design | 3 conditions × 5 tasks × 3 repeats = 45 attempts |
| Seed | 20261015 |
| Images | pinned in `data/image_locks/pilot-01.json` (verified before the run) |

## Headline

| Condition | Resolved | Rate | tokens/attempt | sec/attempt | tool calls/attempt | tests passed |
|---|---|---|---|---|---|---|
| `A_baseline` | 15/15 | **100%** | 355,733 | 104.3 | 30.9 | 522/522 |
| `B_prompt_instructions` | 14/15 | **93.3%** | 336,707 | 137.3 | 28.8 | 446/446 |
| `C_skill` | 15/15 | **100%** | 305,197 | 76.2 | 27.7 | 522/522 |

- **45/45 attempts completed, 0 infrastructure errors.**
- **1490/1490 tests passed.** Total tokens: **14,964,571**.
- Paired effects (task-level bootstrap, 95% CI, n = 5 tasks):
  - `B − A = −0.067`  [−0.200, +0.000]
  - `C − A = +0.000`  [+0.000, +0.000]
- The single unresolved attempt (`psf__requests-3362` / `B` / repeat 2) produced an
  **empty patch** after hitting the cumulative token cap — not a capability signal.

## Interpretation: a ceiling effect

**The run cannot distinguish the three conditions, because all of them resolve
essentially every task.** There is no headroom to detect an accuracy effect. Two
compounding causes:

1. **The task set is easy.** `django__django-11099` is labelled `<15 min fix`;
   `scikit-learn__scikit-learn-10297` and `sympy__sympy-20590` are
   `15 min – 1 hour`. A capable model solves all five regardless of condition.

2. **The baseline prompt leaks the procedure.** The condition-independent base
   system prompt already instructs the agent to *"Read before you write … locate
   the relevant module(s) and understand the current behavior,"* to *"Make the
   smallest change,"* to *"Prefer a targeted fix,"* and to *"Leave the repository
   in a state where the relevant tests pass."* That is most of the B/C workflow
   (steps 1, 2, 4, 5). So Condition A is **not a true no-procedure baseline**, and
   B/C are largely redundant with it — the manipulation has little room to bite.

## Secondary signal (suggestive, not conclusive)

At equal accuracy, **C used the fewest resources**: ~14% fewer tokens than A
(305k vs 356k) and ~10% fewer tool calls (27.7 vs 30.9), with lower wall-clock
(76 vs 104 s/attempt — noisier). Directionally consistent with an on-demand skill
making the agent more economical, but with n = 5 tasks and a ceiling this is not
a reliable effect estimate.

## Threats to validity

- **Ceiling** — the primary endpoint is saturated; no condition separation possible.
- **Prompt leakage** — A already receives ~⅔ of the treatment.
- **Token cap** — the 600k cumulative cap bound **6/45** attempts (A 4, B 2, C 0),
  unevenly. Excluding them changes nothing here (all 39 remaining resolve), but
  the cap should be raised for any future run.
- **Small n** — 5 tasks; the bootstrap CI reflects n = 5 and is correspondingly wide.

## Sensitivity check

Recomputed with the 6 token-cap-truncated attempts removed (n = 39): every
condition resolves **15/15 → 100%**, effects `0.000` for both contrasts. The cap
did not drive the result.

## Reproduce

```bash
python -m skills_experiment preflight --experiment pilot          # verify image digests
python -m skills_experiment run --experiment pilot --grade        # 45 attempts + grading
python -m skills_experiment analyze --experiment pilot            # summary + analysis.json
```

## Files in this record

- `runs.csv` — one row per attempt (status, stop reason, tokens, seconds, tests, image digest).
- `analysis.json` — per-condition stats and paired effects.
- `dataset_manifest.json` — content hash of the exact 5 instance definitions.
- `patches/` — all 45 model patches (`<instance>__<condition>__a<N>.diff`).

Full transcripts and harness logs are intentionally excluded (large); they remain
under `runs/pilot-01/` locally.
