# Mechanism 20-Task A-Only Pilot - Results

**Status:** complete; task set **not frozen**.<br>
**Design:** 10 candidate tasks x condition A x 2 repeats = 20 attempts.<br>
**Model profile:** `deepseek-flash-1017`<br>
**API model string:** `deepseek-flash`<br>
**Plan:** `data/mechanism-20a-pilot-01/plan.json`, seed `20261113`<br>
**Raw jobs:** `SWE-bench_Pro-os/jobs/mechanism-20a-*`<br>
**Artifacts:** `results/mechanism-20a-pilot-01/run_manifest.json`,
`results/mechanism-20a-pilot-01/analysis.json`

This pilot validates the 10 candidate tasks before adding B and C. It is not a
test of the C-B effect, and no B/C outcomes were used for any decision below.

## Provenance

| Item | Value |
|---|---|
| Run window (UTC) | 2026-11-13T20:22:48Z - 2026-11-13T21:14:32Z |
| Launcher wall time | 3,229 s (~54 min) |
| Model profile | `deepseek-flash-1017` |
| Provider model string | `deepseek-flash` (DeepSeek API; 1017 is the service build) |
| Provider / endpoint | `https://api.deepseek.com` |
| Thinking / effort | enabled / medium (mapped to DeepSeek high) |
| Caps | 16,384 response tokens; 1,000,000 cumulative tokens; 80 steps; 3,000 s |
| Harbor | 0.25.0 |
| Harness commit at run | `5f664d1` |
| Pro V2 repo commit | `66f92766bba642462d4bbe5479e83f91f9211862` |
| Verifier mode | `shared` |
| Concurrency | 2 Harbor workers |
| Workflow SHA-256 | `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab` |
| Task checksums / image digests | `run_manifest.json` (10 unique each) |

DeepSeek exposes no sampling seed; the plan seed controls run order only. The
two repeats are provider draws, not guaranteed independent samples.

## Run quality

| Check | Result |
|---|---|
| Completed statuses | 20 / 20 |
| Non-zero launcher statuses | 0 |
| Harbor exceptions | 0 |
| Conditions | A 20, B 0, C 0 |
| Tasks | 10 |
| Repeats | 2 per task |
| Resolved | 18 / 20 |
| Budget exhausted | 9 / 20 |
| Budget type | token budget only; no time-cap exhaustion |
| Skill loaded | 0 / 20 (expected for A) |

The infrastructure portion of the pilot passed cleanly. The task-set gates did
not.

## Task results

Counts are out of two repeats. F2P and P2P are pooled over the two attempts;
budget is the number of attempts that exhausted the token or time cap.

| Task | Intended stratum | Resolved | F2P | P2P | Budget | Patch lines | Tokens | Wall (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `ansible-e22e10` | ceiling | 2/2 | 8/8 | 52/52 | 0/2 | 48 | 683,124 | 161 |
| `openlibrary-e80841` | ceiling | 2/2 | 2/2 | 116/116 | 0/2 | 23 | 512,645 | 108 |
| `openlibrary-25858f` | floor | 2/2 | 26/26 | 66/66 | 2/2 | 410 | 1,020,788 | 134 |
| `qutebrowser-ebfe9b` | floor | 2/2 | 24/24 | 110/110 | 0/2 | 314 | 233,416 | 68 |
| `ansible-83fb24` | new - easy | 2/2 | 2/2 | 42/42 | 0/2 | 20 | 366,716 | 107 |
| `openlibrary-43f9e7` | new - easy | 2/2 | 2/2 | 120/120 | 1/2 | 39 | 842,218 | 118 |
| `openlibrary-53d376` | new - hard | 2/2 | 8/8 | 8/8 | 2/2 | 216 | 1,033,417 | 205 |
| `qutebrowser-e70f5b` | new - hard | 2/2 | 14/14 | 72/72 | 0/2 | 32 | 558,168 | 103 |
| `ansible-1c06c4` | new - medium | 0/2 | 0/8 | 42/42 | 2/2 | 0 | 1,042,094 | 120 |
| `qutebrowser-5fdc83` | new - medium | 2/2 | 22/22 | 92/92 | 2/2 | 117 | 1,035,784 | 167 |

### By intended stratum

| Stratum | Tasks | Attempts | Resolved | Budget | F2P | P2P |
|---|---:|---:|---:|---:|---:|---:|
| ceiling | 2 | 4 | 4/4 | 0/4 | 10/10 | 168/168 |
| floor | 2 | 4 | 4/4 | 2/4 | 50/50 | 176/176 |
| new - easy | 2 | 4 | 4/4 | 1/4 | 4/4 | 162/162 |
| new - hard | 2 | 4 | 4/4 | 2/4 | 22/22 | 80/80 |
| new - medium | 2 | 4 | 2/4 | 4/4 | 22/30 | 134/134 |

## Pilot gates

| Gate | Verdict | Evidence |
|---|---|---|
| Infrastructure | **PASS** | 20/20 `rc=0`; 0 exceptions; all verifier runs completed. |
| Provenance | **PASS** | 10 unique task checksums and 10 unique image digests; no null digests. |
| Runtime | **FAIL** | Three non-floor tasks exhausted both repeats on tokens: `ansible-1c06c4`, `qutebrowser-5fdc83`, `openlibrary-53d376`. `openlibrary-43f9e7` exhausted one of two. All exhaustion was token budget; no time cap. |
| Test stability | **PASS, with saturation** | No task was 1/2. Every task was either 0/2 or 2/2, so the tests were stable but uninformative about within-task variance. |
| Strata | **FAIL** | Both intended floor tasks resolved 2/2. The intended medium pair split 0/2 and 2/2. Both hard tasks and both easy tasks resolved 2/2. Only the ceiling pair matched its label. |

**Decision: do not freeze this 10-task candidate set and do not run B/C on it.**
The pilot succeeded as an infrastructure check but failed the task-validity
gates.

## Observed classification

Applying the predefined outcome rule to the pilot results:

- **2/2 resolved:** `ansible-e22e10`, `openlibrary-e80841`,
  `openlibrary-25858f`, `qutebrowser-ebfe9b`, `ansible-83fb24`,
  `openlibrary-43f9e7`, `openlibrary-53d376`, `qutebrowser-e70f5b`,
  `qutebrowser-5fdc83`.
- **0/2 resolved:** `ansible-1c06c4`.
- **1/2 resolved:** none.

This is a much easier candidate set than the original mechanism set under A:
18/20 attempts resolved, versus the original A resolved rate of 0.70. The new
candidate set does not supply the intended floor anchors, and the hard/easy
labels are not supported by A outcomes.

## What is usable

- **Keep the two ceiling anchors** `ansible-e22e10` and
  `openlibrary-e80841`: both are 2/2 with no budget exhaustion.
- **`ansible-1c06c4` is a credible floor candidate**: 0/2, no patch in either
  attempt, 0/8 F2P, and both attempts hit the token cap. It was labeled medium,
  not floor.
- **The two intended floor tasks are not floor under A**:
  `openlibrary-25858f` and `qutebrowser-ebfe9b` both resolved 2/2. They can be
  reclassified as saturated/ceiling-like tasks, but they cannot remain floor
  anchors.
- **`qutebrowser-5fdc83` and `openlibrary-53d376` are solvable but
  budget-limited**: both resolved 2/2 while exhausting the token cap in both
  repeats. They are poor clean anchors for a runtime gate unless budget
  exhaustion is explicitly accepted for that stratum.
- **The easy and hard pairs are saturated under A** (all 2/2). The hard label
  is not supported by outcomes, even if it is supported by static task shape.

## Recommended next step

Do not add B/C yet. Revise the candidate set first:

1. Treat this pilot as a screening run, not a frozen A arm for the full set.
2. Reclassify or replace the two intended floor tasks. Reclassification alone
   cannot produce a balanced 4-per-stratum set because it would leave too many
   ceiling-like tasks.
3. Keep `ansible-1c06c4` as a floor candidate and screen at least one more
   floor candidate.
4. Screen additional hard/medium candidates, because the current hard pair and
   one medium task are saturated. A second A-only screen of roughly 10
   candidates is the cheapest way to restore a difficulty gradient.
5. Freeze the revised 20-task set only after a second A-only screen passes the
   same gates.
6. Reuse A only for tasks whose IDs, task bytes, images, A condition, model
   profile, budgets, verifier, and agent code are unchanged. Rerun A for every
   replacement task. If pilot A is reused, disclose that A is not interleaved
   with B/C.

No prior A-only screen protocol for the candidate floor/ceiling labels is
recorded in the repository. The labels should therefore be treated as
unvalidated static guesses until a screen is documented.

## Caveats

- A-only, 10 tasks, 2 repeats. This is calibration, not an estimate of any
  condition effect.
- The provider exposes no sampling seed; repeats are not guaranteed independent.
- Shared verifier mode was used; no fresh-sandbox patch replay.
- Budget exhaustion is defined by the existing caps and is not a measure of
  task difficulty by itself.
- The pilot does not justify running B/C on the current candidate set.

## Artifacts

- `results/mechanism-20a-pilot-01/run_manifest.json` - 20-attempt manifest with
  job, return code, wall time, tokens, outcome, task checksum, image digest, and
  verifier mode.
- `results/mechanism-20a-pilot-01/analysis.json` - generated A-only summary;
  B/C sections are empty by design.
- `data/derived/mechanism-20a-pilot-01/` - local `attempts.csv`,
  `events.csv`, and `attempts.json` (gitignored, regenerated from raw jobs).
- `SWE-bench_Pro-os/jobs/mechanism-20a-*` - raw Harbor jobs, transcripts,
  patches, and verifier outputs (outside this repository).
- `data/mechanism-20a-pilot-01/logs/` - launcher and per-job logs (gitignored).

No raw reasoning traces are included in the committed results.
