# Mechanism 20-Task Combined Results

**Status:** combined 120-attempt analysis complete.<br>
**Design:** 20 tasks x 3 conditions x 2 repeats = 120 attempts.<br>
**Model profile:** `deepseek-flash-1017`<br>
**API model string:** `deepseek-flash`<br>
**Frozen set:** `docs/mechanism-study/TASKS_20.md`<br>
**Combined plan:** `data/mechanism-20-combined/plan.json`<br>
**Artifacts:** `results/mechanism-20-combined/run_manifest.json`,
`results/mechanism-20-combined/analysis.json`<br>
**Formal statistical section:** `results/mechanism-20-combined/STATISTICAL_ANALYSIS.md`

This combines:

- 60 attempts from `mechanism-pilot-01` (the original 10 tasks);
- 20 A attempts from the A-only screens for the 10 new tasks;
- 40 B/C attempts from `mechanism-20bc-pilot-01`.

A is reused rather than rerun for the new tasks. The new-task A screens ran
before the B/C extension, so the new-task A arm is not interleaved with B/C.
That is a real design compromise and is called out in the caveats below.

## Provenance

| Item | Value |
|---|---|
| Run window (UTC) | 2026-11-03T21:25:41Z - 2026-11-15T02:51:49Z |
| Model profile | `deepseek-flash-1017` |
| Provider model string | `deepseek-flash` |
| Provider / endpoint | `https://api.deepseek.com` |
| Thinking / effort | enabled / medium |
| Caps | 16,384 response tokens; 1,000,000 cumulative tokens; 80 steps; 3,000 s |
| Harbor | 0.25.0 |
| Pro V2 repo commit | `66f92766bba642462d4bbe5479e83f91f9211862` |
| Verifier mode | `shared` |
| Workflow SHA-256 | `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab` |
| Task checksums / image digests | 20 unique each in `run_manifest.json` |

## Run quality

| Check | Result |
|---|---|
| Completed statuses | 120 / 120 |
| Non-zero launcher statuses | 0 |
| Harbor exceptions | 0 |
| Conditions | A 40, B 40, C 40 |
| Tasks | 20 |
| Repeats | 2 per task-condition |
| Skill loaded | C 40/40; A 0/40; B 0/40 |
| Budget exhausted | 49 / 120 |

All combined launcher rows returned `rc=0`; no exception was recorded.

## Primary endpoints

Task-level means; repeats are averaged within task-condition first.

| Endpoint | A | B | C | C-B mean [95% CI] |
|---|---:|---:|---:|---|
| Resolved | 0.725 | 0.800 | 0.700 | -0.100 [-0.250, +0.025] |
| P1 test-before-edit | 0.100 | 0.100 | 0.100 | 0.000 [-0.100, +0.100] |
| P2 read/search-before-edit | 0.950 | 0.875 | 0.950 | +0.075 [0.000, +0.200] |
| P3 time to first edit (s) | 27.9 | 35.5 | 33.9 | -2.7 [-13.8, +7.9] |
| P4 total tokens | 728,035 | 698,045 | 698,852 | +807 [-46,651, +53,769] |
| Post-edit verification | 0.600 | 0.550 | 0.475 | -0.075 [-0.200, +0.050] |
| Test calls | 3.20 | 2.48 | 4.08 | +1.60 [+0.58, +2.80] |
| Steps | 26.75 | 24.88 | 28.03 | +3.15 [+1.08, +5.33] |
| F2P fraction | 0.856 | 0.857 | 0.815 | -0.042 [-0.131, +0.046] |
| P2P fraction | 0.998 | 0.999 | 0.971 | -0.028 [-0.085, 0.000] |
| Budget exhausted | 0.425 | 0.450 | 0.350 | -0.100 [-0.225, +0.025] |

### Paired direction

Sign p is the unadjusted exact sign test. Formal paired permutation, Wilcoxon,
and Holm-adjusted results are in `STATISTICAL_ANALYSIS.md`.

| Contrast | Endpoint | Mean diff | 95% CI | W/L/T | Sign p |
|---|---|---:|---|---:|---:|
| C-B | Resolved | -0.100 | [-0.250, +0.025] | 1/4/15 | 0.375 |
| C-B | Test calls | +1.600 | [+0.575, +2.800] | 12/3/5 | 0.035 |
| C-B | Steps | +3.150 | [+1.075, +5.325] | 15/5/0 | 0.041 |
| C-B | Post-edit verification | -0.075 | [-0.200, +0.050] | 2/5/13 | 0.453 |
| B-A | Resolved | +0.075 | [-0.050, +0.200] | 3/1/16 | 0.625 |
| B-A | Test calls | -0.725 | [-1.300, -0.200] | 5/10/5 | 0.302 |
| B-A | Steps | -1.875 | [-3.500, -0.225] | 4/13/3 | 0.049 |
| C-A | Resolved | -0.025 | [-0.175, +0.100] | 3/3/14 | 1.000 |
| C-A | Total tokens | -29,183 | [-65,422, +7,748] | 4/16/0 | 0.012 |

## Strata

| Stratum | Tasks | A resolved | B resolved | C resolved |
|---|---:|---:|---:|---:|
| Ceiling | 4 | 1.000 | 1.000 | 1.000 |
| Floor | 3 | 0.000 | 0.167 | 0.167 |
| Easy | 4 | 1.000 | 1.000 | 1.000 |
| Medium | 4 | 0.875 | 1.000 | 0.625 |
| Hard | 5 | 0.600 | 0.700 | 0.600 |

The ceiling and easy strata are saturated. The medium stratum carries most of
the C deficit: B resolved 1.00 of task means, C resolved 0.625. The floor
stratum is almost completely saturated at failure; one B and one C attempt
resolved `openlibrary-0dc5b2`.

## Resolved by task

Counts are out of two repeats; budget is the number of attempts that exhausted
the token or time cap.

| Task | Stratum | A | B | C | Budget A/B/C |
|---|---|---:|---:|---:|---|
| `ansible-e22e10` | ceiling | 2 | 2 | 2 | 0/1/0 |
| `ansible-e9e600` | ceiling | 2 | 2 | 2 | 0/0/0 |
| `openlibrary-e80841` | ceiling | 2 | 2 | 2 | 0/0/0 |
| `qutebrowser-3e21c8` | ceiling | 2 | 2 | 2 | 2/2/1 |
| `ansible-1c06c4` | floor | 0 | 0 | 0 | 2/2/2 |
| `openlibrary-0dc5b2` | floor | 0 | 1 | 1 | 2/2/2 |
| `openlibrary-b67138` | floor | 0 | 0 | 0 | 2/2/2 |
| `ansible-12734f` | easy | 2 | 2 | 2 | 0/0/0 |
| `ansible-83fb24` | easy | 2 | 2 | 2 | 0/0/0 |
| `qutebrowser-96b997` | easy | 2 | 2 | 2 | 0/0/0 |
| `qutebrowser-990291` | easy | 2 | 2 | 2 | 0/0/0 |
| `ansible-b748ed` | hard | 1 | 1 | 1 | 1/1/0 |
| `ansible-d62496` | hard | 2 | 2 | 2 | 0/0/1 |
| `openlibrary-630221` | hard | 1 | 0 | 1 | 2/2/2 |
| `qutebrowser-c09e14` | hard | 0 | 2 | 1 | 0/1/0 |
| `qutebrowser-ec2dcf` | hard | 2 | 2 | 1 | 2/2/1 |
| `ansible-5e3696` | medium | 2 | 2 | 0 | 2/2/1 |
| `ansible-6cc974` | medium | 2 | 2 | 2 | 0/0/0 |
| `openlibrary-6e889f` | medium | 1 | 2 | 2 | 1/0/1 |
| `openlibrary-d8162c` | medium | 2 | 2 | 1 | 1/1/1 |

The C-B resolved difference is concentrated in five tasks:

- `openlibrary-630221`: +1 for C (B 0, C 1)
- `qutebrowser-c09e14`: -1 for C (B 2, C 1)
- `qutebrowser-ec2dcf`: -1 for C (B 2, C 1)
- `ansible-5e3696`: -2 for C (B 2, C 0)
- `openlibrary-d8162c`: -1 for C (B 2, C 1)

All other 15 tasks have identical B and C resolved counts.

## Reading the result

- **C-B resolved is -0.10**, but the interval includes zero and the sign test is
  not significant (1 win, 4 losses, 15 ties). The direction is negative, not a
  clean effect.
- **C is behaviorally heavier than B**: +1.6 test calls and +3.15 steps per task,
  with bootstrap intervals excluding zero and unadjusted sign tests
  p = 0.035 / 0.041. After Holm correction across the 10 secondary endpoints,
  neither survives (Holm p = 0.085 / 0.119). Post-edit verification is slightly
  lower for C, but its interval includes zero.
- **C-B total tokens are essentially null** (+807 tokens; interval spans zero).
  The extra test calls and steps did not translate into a clear token
  difference.
- **B is leaner than A on steps and test calls**, while the B-A resolved
  difference is positive but uncertain. B also has the best resolved point
  estimate (0.800 versus A 0.725 and C 0.700).
- **The medium stratum drives the C deficit**: B 1.000 vs C 0.625. Ceiling and
  easy are saturated, and hard is roughly flat (B 0.700 vs C 0.600).
- **The floor stratum remains mostly floor**: A 0/3, B/C 0.167 each, with the
  only resolutions coming from `openlibrary-0dc5b2`.

## Caveats

- The new-task A arm was run before B/C, not interleaved with it. Provider drift,
  machine load, and run-window differences could confound A versus B/C for those
  tasks.
- The original 10 tasks have interleaved A/B/C evidence; the 10 new tasks do not.
- The frozen 20-task set is 3 floor / 5 hard, not a perfectly balanced 4 per
  stratum. Stratum results are descriptive.
- Several hard tasks are resolved at or near the token cap — for example,
  `qutebrowser-ec2dcf` is 2/2 under B with both repeats capped, and
  `ansible-d62496` has a C cap hit — while `ansible-b748ed` and
  `openlibrary-630221` are only 1/2. "Hard" here is a mixed difficulty label,
  not a uniform failure band.
- DeepSeek exposes no sampling seed; repeats are provider draws, not guaranteed
  independent samples.
- Shared verifier mode was used; no fresh-sandbox patch replay.
- The result is a descriptive 20-task extension. It does not establish a
  confirmatory C-B effect.

## Artifacts

- `results/mechanism-20-combined/run_manifest.json` - 120-attempt manifest with
  job, return code, wall time, tokens, outcome, task checksum, image digest, and
  verifier mode.
- `results/mechanism-20-combined/analysis.json` - task-level condition stats,
  paired effects, bootstrap intervals, sign tests, rank-biserial effects, and
  strata.
- `data/mechanism-20-combined/plan.json` - combined 120-attempt analysis plan.
- `data/mechanism-20-combined/run_status.jsonl` - merged launcher statuses.
- `data/derived/mechanism-20-combined/attempts.json` / `attempts.csv` - local
  combined attempt table (gitignored, regenerated).
- Raw jobs: `SWE-bench_Pro-os/jobs/mechanism-v2-*`,
  `mechanism-20a-*`, `mechanism-20a2-*`, `mechanism-20a3-*`,
  `mechanism-20bc-*`.
- Frozen set: `docs/mechanism-study/TASKS_20.md` and
  `data/mechanism-20-final/tasks.json`.

No raw reasoning traces are included in the committed results.
