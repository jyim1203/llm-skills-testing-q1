# `main-local-pilot-01` -- calibration run

**Status: validation/calibration only. Not pooled with `main-local-01`.**

- Date: 2026-10-24 (UTC)
- Model: `local-qwen-sampling` (Qwen 3.5 9B Q4_K_M, `qwen3.5-9b-agent-64k`)
- Decoding: temperature 0.2, 8,192 max tokens per response
- Budgets: 80 steps, 1,500,000 cumulative tokens, 1,800 s
- Tasks: 6 (the five frozen `pilot-01` tasks + `pytest-dev__pytest-5495`)
- Design: 6 tasks x 3 conditions x 1 repeat = 18 attempts
- Image lock: `data/image_locks/main-local-pilot-01.json`
- Framework commit at run start: `321eeb7`

## Result

18/18 attempts completed, **0 infrastructure errors**, 10 resolved / 8 unresolved.

| Task | A baseline | B prompt | C skill |
|---|---|---|---|
| `django__django-11099` | resolved | resolved | resolved |
| `matplotlib__matplotlib-22835` | unresolved | unresolved | unresolved |
| `psf__requests-3362` | unresolved | resolved | resolved |
| `pytest-dev__pytest-5495` | unresolved | unresolved | unresolved |
| `scikit-learn__scikit-learn-10297` | resolved | resolved | resolved |
| `sympy__sympy-20590` | resolved | unresolved | resolved |
| **Resolved** | **3/6 (50%)** | **3/6 (50%)** | **4/6 (67%)** |

C loaded the skill in 6/6 attempts. C was never worse than A or B on any task in
this sample.

Task-level bootstrap (2,000 resamples, task as the resampling unit):

- B - A: +0.000, 95% CI [-0.500, +0.500]
- C - A: +0.167, 95% CI [+0.000, +0.500]

With one repeat per cell these intervals are exploratory, not a main result.

## Cost and stop reasons

| Condition | Avg steps | Avg tokens | `stop` | `token_budget` | `length` |
|---|---:|---:|---:|---:|---:|
| A baseline | 37.8 | 919,360 | 1 | 3 | 2 |
| B prompt | 55.5 | 1,294,025 | 2 | 4 | 0 |
| C skill | 60.3 | 1,261,654 | 2 | 3 | 1 |

Wall time was 54m14s including grading.

## What the pilot showed

- The new pytest task and image work end to end, and grading is clean.
- `require_load = true` works: C called `load_skill` in every attempt.
- The 1.5M cumulative token budget was binding for 10/18 attempts, and the 8,192
  per-response cap caused 3/18 `length` stops. The token cap, not the 80-step
  cap, usually ended the attempt.
- The discriminating tasks were `requests` (A failed with a 24k over-edit; B and
  C resolved) and `sympy` (A and C resolved; B hit the token cap and produced an
  empty patch). `matplotlib` and `pytest` failed in all three conditions.
- This motivated the main run's calibrated budgets: 2,500,000 cumulative tokens
  and 16,384 per response.

## Caveats

- One repeat per (task, condition); not a main result.
- The run rows record the actual 1,500,000/8,192 budgets. `main-local-pilot.toml`
  now matches the main run's 2.5M/16,384 settings for any future re-run.
- The harness reports `tests_passed/tests_total` over each task's configured
  FAIL_TO_PASS/PASS_TO_PASS sets; the aggregate denominators differ when a patch
  is empty, so compare resolved status rather than raw test totals.
- Artifacts are under `runs/main-local-pilot-01/` (local, not committed).
