# Mechanism Pilot 01 — Results

**Status:** complete  
**Design:** 10 tasks × 3 conditions × 2 repeats = 60 attempts  
**Workflow:** canonical v2  
**Model:** `deepseek-flash-1017`  
**Task set:** `docs/mechanism-study/TASKS.md`  
**Plan:** `data/mechanism-pilot-01/plan.json`, seed `20261103`  
**Raw jobs:** `SWE-bench_Pro-os/jobs/mechanism-v2-*`  
**Derived tables:** `data/derived/mechanism-pilot-01/{attempts.csv,events.csv}`

## Run quality

| Check | Result |
|---|---|
| Completed statuses | 60 / 60 |
| Non-zero launcher statuses | 0 |
| Harbor exceptions | 0 |
| Conditions | A 20, B 20, C 20 |
| Tasks | 10 |
| Repeats | 2 per task-condition |
| C skill loaded | 20 / 20 |
| A/B skill loaded | 0 / 20 each |
| Budget exhausted | 27 / 60 |
| Smoke attempts included | no |

The initial launcher stopped after 22/60; it was resumed from order 23 with a
detached process. All 60 attempt statuses are `rc=0`.

## Primary endpoints

Task-level means (two repeats averaged first):

| Endpoint | A | B | C | C−B mean [95% CI] |
|---|---:|---:|---:|---|
| P1 test-before-edit | 0.10 | 0.05 | 0.05 | 0.00 [0.00, 0.00] |
| P2 read/search-before-edit | 0.95 | 0.95 | 0.95 | 0.00 [0.00, 0.00] |
| P3 time to first edit (s) | 27.9 | 30.6 | 31.5 | +0.9 [−11.5, +13.8] |
| P4 total tokens | 694,253 | 658,440 | 678,071 | +19,631 [−53,056, +109,922] |

P1 and P2 are saturated or near-floor, so they do not discriminate. P3 and P4
are noisy and have intervals spanning zero.

## Outcome and secondary behavior

| Endpoint | A | B | C | C−B mean [95% CI] |
|---|---:|---:|---:|---|
| Resolved rate | 0.70 | 0.85 | 0.65 | −0.20 [−0.45, 0.00] |
| F2P fraction | 0.835 | 0.924 | 0.818 | −0.106 [−0.229, +0.006] |
| P2P fraction | 0.995 | 0.998 | 0.938 | −0.060 [−0.180, 0.00] |
| Post-edit verification | 0.65 | 0.55 | 0.40 | −0.15 [−0.30, 0.00] |
| Test calls | 2.85 | 2.15 | 4.10 | +1.95 [+0.40, +3.80] |
| Steps | 23.8 | 22.0 | 25.7 | +3.7 [+0.8, +7.0] |
| Tool calls | 31.1 | 28.2 | 30.4 | +2.2 [−0.7, +5.3] |
| Budget exhausted | 0.45 | 0.50 | 0.40 | −0.10 [−0.30, +0.10] |

Resolved by task (counts out of 2 repeats):

| Task | A | B | C | Budget A/B/C | P2P failures A/B/C |
|---|---:|---:|---:|---|---|
| ansible-12734f | 2 | 2 | 2 | 0/0/0 | 0/0/0 |
| ansible-5e3696 | 2 | 2 | 0 | 2/2/1 | 0/0/0 |
| ansible-d62496 | 2 | 2 | 2 | 0/0/1 | 0/0/0 |
| ansible-e9e600 | 2 | 2 | 2 | 0/0/0 | 0/0/0 |
| openlibrary-0dc5b2 | 0 | 1 | 1 | 2/2/2 | 2/2/2 |
| openlibrary-b67138 | 0 | 0 | 0 | 2/2/2 | 2/0/51 |
| openlibrary-d8162c | 2 | 2 | 1 | 1/1/1 | 0/0/0 |
| qutebrowser-3e21c8 | 2 | 2 | 2 | 2/2/1 | 0/0/0 |
| qutebrowser-96b997 | 2 | 2 | 2 | 0/0/0 | 0/0/0 |
| qutebrowser-c09e14 | 0 | 2 | 1 | 0/1/0 | 0/0/0 |

## Reading the result

- The manipulation check passed: C loaded the skill in every attempt; A/B never did.
- **B has the best point estimate** (0.85 resolved vs A 0.70, C 0.65). The C−B
  interval for resolved rate reaches zero, so this is descriptive, not a
  definitive effect.
- **C did not improve behavior on the primary endpoints.** P1/P2 are
  saturated/near-floor; P3/P4 intervals span zero.
- **C was more expensive behaviorally**: more test calls and more steps. It also
  had lower post-edit verification and lower P2P preservation.
- The P2P gap is concentrated: one C attempt on `openlibrary-b67138` passed only
  4/53 P2P tests, while the other C attempt passed 51/53. That is a large
  variance/regression signal worth inspecting, not a stable condition effect.
- Task effects dominate. Several tasks are all-resolved or all-unresolved; the
  B−A point estimate is driven by a small number of tasks.

## Caveats

- n = 10 tasks, 2 repeats; this is a descriptive mechanism pilot.
- P1/P2 were chosen after the pilot baseline showed post-edit verification was
  saturated; they still turned out saturated/near-floor.
- The v2 workflow is largely generic; A already adhered to much of it.
- Budget exhaustion affects 27/60 attempts; outcome is “resolved within budget.”
- Shared verifier was used; no fresh-sandbox patch replay.
- C’s lower P2P fraction may reflect a few harmful patches and should be checked
  trace-by-trace before any general claim.

## Next

1. Inspect the C `b67138` patches and the C failures on `5e3696`/`c09e14`.
2. Compare C/B tool sequences to see whether skill loading changes verification
   or editing behavior.
3. Decide whether the mechanism manipulation is strong enough to justify a
   larger run. The current result is null-to-negative for C relative to B.
