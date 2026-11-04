# Mechanism Pilot 01 — Results

**Status:** complete<br>
**Design:** 10 tasks × 3 conditions × 2 repeats = 60 attempts<br>
**Workflow:** canonical v2<br>
**Model profile:** `deepseek-flash-1017`<br>
**API model string:** `deepseek-flash`<br>
**Task set:** `docs/mechanism-study/TASKS.md`<br>
**Plan:** `data/mechanism-pilot-01/plan.json`, seed `20261103`<br>
**Raw jobs:** `SWE-bench_Pro-os/jobs/mechanism-v2-*`<br>
**Artifacts:** `results/mechanism-pilot-01/run_manifest.json`, `analysis.json`

## Provenance

| Item | Value |
|---|---|
| Run window (UTC) | 2026-11-03T21:25:41Z – 2026-11-04T00:27:44Z |
| Model profile | `deepseek-flash-1017` |
| Provider model string | `deepseek-flash` (DeepSeek API; 1017 is the service build) |
| Provider / endpoint | `https://api.deepseek.com` |
| Thinking / effort | enabled / medium (mapped to DeepSeek high) |
| Caps | 16,384 response tokens; 1,000,000 cumulative tokens; 80 steps; 3,000 s |
| Harbor | 0.25.0 |
| Harness commit at run | `a13fe23` |
| Pro V2 repo commit | `66f92766bba642462d4bbe5479e83f91f9211862` |
| Verifier mode | `shared` |
| Concurrency | 2 Harbor workers |
| Workflow SHA-256 | `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab` |
| Task checksums / image digests | `docs/mechanism-study/TASKS.md` |

The first attempt started at 21:25:41Z, about two minutes before `a13fe23` was
committed; `a13fe23` differs from `13a0588` only by the launcher script. The
model profile has no dated provider alias and the API exposes no sampling seed;
the plan seed controls order only. Repeats are therefore provider
nondeterminism, not guaranteed independent samples. `run_manifest.json` records
the 60 jobs, return codes, wall time, task checksum, image digest, resolved
status, tokens, stop reason, and verifier mode.

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

### Dispersion (task-level median, SD)

| Endpoint | A | B | C |
|---|---:|---:|---:|
| Resolved | 1.00 (0.48) | 1.00 (0.34) | 0.75 (0.41) |
| P1 test-before-edit | 0.00 (0.21) | 0.00 (0.16) | 0.00 (0.16) |
| P2 read/search-before-edit | 1.00 (0.16) | 1.00 (0.16) | 1.00 (0.16) |
| P3 time to first edit | 22.9 (20.1) | 27.1 (23.1) | 24.5 (19.4) |
| P4 total tokens | 799,385 (356,307) | 724,771 (387,679) | 823,785 (369,665) |
| Post-edit verification | 0.75 (0.41) | 0.50 (0.37) | 0.50 (0.39) |
| Test calls | 2.50 (1.96) | 2.25 (1.36) | 2.75 (3.61) |
| Steps | 26.5 (6.7) | 24.5 (7.5) | 27.25 (8.2) |
| F2P fraction | 1.00 (0.32) | 1.00 (0.19) | 1.00 (0.30) |
| P2P fraction | 1.00 (0.01) | 1.00 (0.01) | 1.00 (0.17) |

P2P is defined for 8 tasks; `openlibrary-d8162c` and `qutebrowser-3e21c8` have
no P2P tests.

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

All values in this table are task-level means: each task counts equally after
averaging its two repeats. The F2P/P2P means therefore differ from pooled test
counts, where a task with many tests carries more weight.

### Paired direction and sign tests

| Contrast | Endpoint | Mean diff | Median diff | 95% CI | W/L/T | Sign p | Rank-biserial |
|---|---|---:|---:|---|---:|---:|---:|
| C−B | Resolved | −0.200 | 0.000 | [−0.450, 0.000] | 0/3/7 | 0.250 | −1.000 |
| C−B | Post-edit verification | −0.150 | 0.000 | [−0.300, 0.000] | 0/3/7 | 0.250 | −1.000 |
| C−B | Test calls | +1.950 | +0.500 | [+0.400, +3.800] | 7/1/2 | 0.070 | 0.861 |
| C−B | Steps | +3.700 | +1.000 | [+0.800, +7.000] | 8/2/0 | 0.109 | 0.655 |
| C−B | F2P fraction | −0.106 | 0.000 | [−0.229, +0.006] | 1/4/5 | 0.375 | −0.733 |
| C−B | P2P fraction | −0.060 | 0.000 | [−0.180, 0.000] | 0/1/7 | 1.000 | −1.000 |
| B−A | Resolved | +0.150 | 0.000 | [0.000, +0.350] | 2/0/8 | 0.500 | 1.000 |
| C−A | Resolved | −0.050 | 0.000 | [−0.350, +0.200] | 2/2/6 | 1.000 | −0.200 |

P2P has n = 8 tasks; other rows have n = 10. W/L/T counts tasks in which the
first condition was better, worse, or tied. The exact sign tests are descriptive
and are not corrected for multiple comparisons.

## Stratification

| Stratum | Tasks | A resolved | B resolved | C resolved |
|---|---|---:|---:|---:|
| Ceiling | 2 | 1.000 | 1.000 | 1.000 |
| Floor | 2 | 0.000 | 0.250 | 0.250 |
| New — easy | 2 | 1.000 | 1.000 | 1.000 |
| New — medium | 2 | 1.000 | 1.000 | 0.250 |
| New — hard | 2 | 0.500 | 1.000 | 0.750 |
| New — pooled | 6 | 0.833 | 1.000 | 0.667 |

Test calls and P2P preservation:

| Stratum | Test calls A/B/C | P2P A/B/C |
|---|---|---|
| Ceiling | 3.25 / 2.50 / 3.00 | 1.000 / 1.000 / 1.000 |
| Floor | 1.00 / 1.00 / 1.00 | 0.981 / 0.991 / 0.755 |
| New — easy | 2.75 / 2.00 / 2.50 | 1.000 / 1.000 / 1.000 |
| New — medium | 2.50 / 2.25 / 4.25 | 1.000 / 1.000 / 1.000 |
| New — hard | 4.75 / 3.00 / 9.75 | 1.000 / 1.000 / 1.000 |
| New — pooled | 3.33 / 2.42 / 5.50 | 1.000 / 1.000 / 1.000 |

The C deficit is concentrated in the new-medium stratum and in the floor
stratum’s P2P result. The ceiling and new-easy strata are saturated for all
three conditions.

## Resolved by task

Counts are out of 2 repeats. Budget is the number of attempts that exhausted
the token or time cap; P2P failures are failed pass-to-pass tests.

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

## Exploratory case notes

These are structured observations from the traces, not blinded qualitative
coding.

- **C / `ansible-5e3696` (both failed).** The two C attempts made 7 edits each,
  made 5 and 10 test calls, and ended with no post-edit verification; they
  reached only 5/7 and 4/7 F2P. Both A and B resolved the task. More test
  activity did not translate into a completed fix.
- **C / `openlibrary-b67138` (P2P collapse).** One C attempt produced a 140-line
  MARC patch that passed only 4/53 P2P tests; the other produced a 163-line
  patch and passed 51/53. B’s near-miss passed 9/11 F2P with 53/53 P2P. The
  condition-level P2P gap is therefore one harmful patch plus high variance, not
  a consistent C behavior.
- **B / `qutebrowser-c09e14` (clean sweep).** B resolved both repeats (5/5 F2P);
  A resolved neither (4/5 F2P both times); C resolved one. This task contributes
  directly to the B−A resolved point estimate.
- **C / `openlibrary-d8162c` (variance).** One C attempt submitted an empty patch
  at the budget limit; the other resolved. The task is F2P-only (no P2P tests).

## Reading the result

- The manipulation check passed: C loaded the skill in every attempt; A/B never
  did.
- **B has the best point estimate** (0.85 resolved vs A 0.70, C 0.65). The C−B
  interval reaches zero; the sign test is not significant (three C losses, seven
  ties). This is descriptive, not a definitive effect.
- **C did not improve behavior on the primary endpoints.** P1/P2 are
  saturated/near-floor; P3/P4 intervals span zero.
- **C was more expensive behaviorally.** It made more test calls and took more
  steps; the C−B bootstrap intervals for those two endpoints exclude zero, while
  their exact sign tests are only suggestive (p = 0.070 and 0.109). C also had
  lower post-edit verification.
- **The P2P gap is not a general C effect.** It is concentrated in one
  `openlibrary-b67138` patch; the other C attempt there preserved 51/53 P2P.
- **Task and stratum effects dominate.** Ceiling and new-easy tasks are
  saturated; most of the resolved-rate point estimate comes from a few tasks
  (notably `ansible-5e3696`, `qutebrowser-c09e14`, and `openlibrary-0dc5b2`).

## Caveats

- n = 10 tasks, 2 repeats; this is a descriptive mechanism pilot. No claim of a
  general skill effect is warranted.
- P1/P2 were chosen after the pilot baseline showed post-edit verification was
  saturated; they still turned out saturated/near-floor.
- The v2 workflow is largely generic; A already adhered to much of it.
- Budget exhaustion affects 27/60 attempts; outcome is “resolved within budget.”
- The provider exposes no sampling seed, so repeats are not guaranteed
  independent; the API model string is undated.
- Shared verifier was used; no fresh-sandbox patch replay.
- C’s lower P2P fraction is driven by one harmful patch and should not be
  generalized without trace-level review.
- The `test_before_edit` detector is heuristic and near-floor in all conditions.

## Artifacts

- `results/mechanism-pilot-01/run_manifest.json` — 60-attempt manifest with job,
  return code, wall time, tokens, outcome, checksum, and image digest.
- `results/mechanism-pilot-01/analysis.json` — task-level condition stats,
  paired effects, sign tests, rank-biserial effects, and strata.
- `docs/mechanism-study/TASKS.md` — frozen task list, checksums, and image
  digests.
- `scripts/summarize_mechanism_run.py` — regenerates the manifest and analysis
  from the derived attempt table and Harbor trial results.
- `data/derived/mechanism-pilot-01/` — local derived `attempts.csv`,
  `events.csv`, and `attempts.json` (gitignored, regenerated from raw jobs).
- `SWE-bench_Pro-os/jobs/mechanism-v2-*` — raw Harbor jobs, transcripts,
  patches, and verifier outputs (outside this repository).

No raw reasoning traces are included in the committed results.

## Next

1. Run blinded trace-level coding on 2–3 traces per condition and replay the
   `b67138` C patch in a fresh sandbox.
2. Check whether the C test-call increase is useful verification or redundant
   probing, and whether it explains the new-medium deficit.
3. Decide whether the manipulation is strong enough to justify a larger run.
   The current result is null-to-negative for C relative to B.
