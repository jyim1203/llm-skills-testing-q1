# Task Selection and 20-Task Extension Plan

Status: the 20-task set is frozen as of 2026-11-14. The completed
`mechanism-pilot-01` study remains frozen; this document records the selection
criteria and the final extension set without discarding the existing 60
attempts.

## Project in brief

The mechanism study asks whether the *delivery* of workflow guidance changes how
a coding agent works, not just whether it resolves a task.

| Condition | What the agent gets |
|---|---|
| **A — baseline** | Base prompt and task context only |
| **B — direct prompt** | A plus the v2 workflow pasted into the system prompt |
| **C — skill** | A plus the same v2 workflow packaged as `SKILL.md`, loaded through `load_skill` |

The primary contrast is **C vs B**. The reported study uses DeepSeek V4.1 Flash
(`deepseek-flash-1017`) on 10 SWE-bench Pro V2 tasks, with 2 repeats per
task-condition: 60 attempts. Primary endpoints are test-before-edit,
read/search-before-edit, time to first edit, and total tokens; resolved rate is
exploratory.

Reference result: A/B/C resolved rates were 0.70 / 0.85 / 0.65, with C-B
= -0.20 [95% CI -0.45, 0.00]. P1/P2 were saturated or near-floor and P3/P4
intervals spanned zero. See
[`../../results/mechanism-pilot-01/RESULTS.md`](../../results/mechanism-pilot-01/RESULTS.md)
and [`PROTOCOL.md`](PROTOCOL.md).

## Selection criteria

The original 10 tasks were frozen before the mechanism run. New tasks should use
the same rules and be frozen before their first B/C attempt.

1. **Benchmark and version.** Use SWE-bench Pro V2 at the pinned benchmark commit
   `66f92766bba642462d4bbe5479e83f91f9211862`; use task definitions and images
   from that checkout.
2. **Stratified difficulty.** Keep known ceiling/floor anchors and add a static
   difficulty mix. The current set has 2 ceiling, 2 floor, 2 easy, 2 medium, and
   2 hard tasks. For 20 tasks, the clean target is 4 per stratum.
3. **Outcome-blind selection.** Use only condition-A pilot outcomes and static
   task properties (repository, files/lines changed, F2P/P2P counts, `hard`
   label). Never select or replace a task based on B/C outcomes.
4. **Valid evaluation data.** Each task must have a working Pro V2 task
   definition, at least one FAIL_TO_PASS test, and a usable verifier. P2P = 0 is
   allowed but must be marked as an F2P-only task.
5. **Runnable image and budget.** The GHCR task image must pull reliably and run
   inside Harbor's 3,000-second cap with the existing 80-step / 1,000,000-token
   budget. Account for roughly 40 GB of image and job storage.
6. **Repository balance.** Pro V2's Python subset has only three repositories
   (`ansible/ansible`, `internetarchive/openlibrary`,
   `qutebrowser/qutebrowser`), so multiple tasks per repository are allowed.
   Keep the mix reasonably balanced; the current split is 4 / 3 / 3.
7. **Bounded task shape.** Prefer tasks with a clear, testable behavior change.
   Very large cross-file tasks are useful as floor anchors but should not
   dominate the set; the current 888-line OpenLibrary task is the largest
   example.
8. **Freeze before running.** Record task IDs, strata, task checksums, and image
   digests before the first new attempt. No replacement after B/C outcomes.
9. **Keep the manipulation fixed.** New tasks use the same v2 workflow body
   (`586b1376...`), model profile, prompts, budgets, verifier mode, and A/B/C
   condition definitions as `mechanism-pilot-01`.

Full task IDs and checksums for the current set are in
[`TASKS.md`](TASKS.md); the table below uses short IDs.

## Tasks already in the study

| # | Task | Repository | Stratum | Files / lines | F2P | P2P |
|---:|---|---|---|---:|---:|---:|
| 1 | `ansible-e9e600` | ansible/ansible | ceiling | 2 / 96 | 8 | 20 |
| 2 | `qutebrowser-3e21c8` | qutebrowser/qutebrowser | ceiling | 1 / 59 | 1869 | 0 |
| 3 | `openlibrary-0dc5b2` | internetarchive/openlibrary | floor (known) | 1 / 62 | 6 | 55 |
| 4 | `openlibrary-b67138` | internetarchive/openlibrary | floor (expected) | 6 / 888 | 11 | 53 |
| 5 | `qutebrowser-96b997` | qutebrowser/qutebrowser | new — easy | 2 / 24 | 17 | 161 |
| 6 | `ansible-12734f` | ansible/ansible | new — easy | 3 / 26 | 1 | 4 |
| 7 | `openlibrary-d8162c` | internetarchive/openlibrary | new — medium | 3 / 74 | 18 | 0 |
| 8 | `ansible-5e3696` | ansible/ansible | new — medium | 5 / 94 | 7 | 2 |
| 9 | `ansible-d62496` | ansible/ansible | new — hard | 3 / 35 | 22 | 92 |
| 10 | `qutebrowser-c09e14` | qutebrowser/qutebrowser | new — hard | 4 / 45 | 5 | 100 |

Composition: 4 Ansible, 3 OpenLibrary, 3 qutebrowser; 2 tasks per stratum;
2 repeats; 60 attempts. `qutebrowser-3e21c8` and `openlibrary-d8162c` have
P2P = 0, so their outcome is F2P-only.

## Extension to 20 tasks

Adding 10 tasks gives 20 total. Two designs preserve the existing 60 attempts:

| Design | Existing attempts | New attempts | Total |
|---|---:|---:|---:|
| 20 tasks x 3 conditions x 2 repeats | 60 | 60 | 120 |
| 20 tasks x 3 conditions x 3 repeats | 60 | 120 | 180 |

**Two repeats (exact reuse).** Run the 10 new tasks with 3 conditions and 2
repeats: 60 new attempts. Combine with the existing 60 for a balanced 20-task,
2-repeat analysis. This is the cleanest option if the goal is to keep every old
run and avoid rerunning anything.

**Three repeats (stronger within-task view).** Run the 10 new tasks with 3
conditions and 3 repeats (90 attempts), plus one third repeat for each of the 10
existing tasks across 3 conditions (30 attempts). That is 120 new attempts;
combined with the existing 60, the result is a balanced 20-task, 3-repeat set.
Do not run old tasks with only 2 repeats and new tasks with 3; that would make
the task-level averages incomparable.

The A-only calibration plan for these 10 candidates is in
[`A_PILOT_PLAN.md`](A_PILOT_PLAN.md).

## A-only pilot result (2026-11-13)

The 20-attempt A-only pilot completed with 20/20 `rc=0` and 18/20 resolved, but
it did **not** pass the task-validity gates. Both intended floor tasks resolved
2/2, the intended medium pair split 0/2 and 2/2, both hard tasks resolved 2/2,
and three non-floor tasks exhausted both repeats on tokens. The candidate set is
therefore not frozen; do not run B/C on it. See
[`../../results/mechanism-20a-pilot-01/RESULTS.md`](../../results/mechanism-20a-pilot-01/RESULTS.md).

## Final 20-task set (frozen 2026-11-14)

The final set combines the original 10 tasks with 10 tasks selected only from
A-only evidence. Task IDs, checksums, image digests, and observed A outcomes are
in [`TASKS_20.md`](TASKS_20.md) and
`data/mechanism-20-final/tasks.json`.

New tasks:

| Stratum | Task |
|---|---|
| ceiling | `ansible-e22e10`, `openlibrary-e80841` |
| easy | `ansible-83fb24`, `qutebrowser-990291` |
| floor | `ansible-1c06c4` |
| medium | `ansible-6cc974`, `openlibrary-6e889f` |
| hard | `qutebrowser-ec2dcf`, `ansible-b748ed`, `openlibrary-630221` |

Composition: **4 ceiling, 4 easy, 3 floor, 4 medium, 5 hard**; repositories are
**9 Ansible, 6 OpenLibrary, 5 qutebrowser**. The 3-floor / 5-hard imbalance was
accepted rather than screening more floor candidates. `openlibrary-53d376` was
dropped as redundant with the other token-capped 2/2 tasks. No B/C outcome was
used for selection, and no replacement is allowed after B/C begins.

## Keeping the existing runs

Keep `mechanism-pilot-01`, its plan, and its raw Harbor jobs unchanged. Do not
overwrite `data/mechanism-pilot-01/plan.json`, and do not reuse completed job
names: Harbor job names are deterministic and would collide.

Recommended layout:

- new experiment ID, for example `mechanism-pilot-02` or `mechanism-20`;
- new selection/plan under `data/mechanism-20/` (or a clearly named equivalent);
- new job prefix, for example `mechanism-v2b-*`, instead of `mechanism-v2-*`;
- new randomized plan seed, with conditions and repeats interleaved;
- new task checksums and image digests recorded before the run.

For the 2-repeat design, the new experiment contains only the 10 new tasks. For
the 3-repeat design, it contains the 10 new tasks at repeats 1-3 and the 10 old
tasks at repeat 3 only. In both cases, the existing 60 attempts stay in
`mechanism-pilot-01` and are combined at analysis time.

Record the new run window, model profile, workflow hash, Pro V2 commit, Harbor
version, verifier mode, and image digests. DeepSeek exposes no sampling seed, so
new repeats are provider draws, not guaranteed independent samples.

## Before running the extension

- Freeze the 10 new task IDs and strata in a new selection file.
- Pull and record the new image digests; verify the old digests are unchanged.
- Confirm the v2 workflow hash still matches `586b1376...`.
- Confirm A/B/C still use the same prompts and condition definitions.
- Generate and record a new randomized order with a new seed.
- Run a dry-run of the new plan and check for job-name collisions.
- Analyze by task, averaging repeats before comparing conditions; do not pool
  raw attempts across tasks.
