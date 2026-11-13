# A-Only Pilot Plan for the 20-Task Extension

Status: run completed 2026-11-13; task set not frozen. See
[`../../results/mechanism-20a-pilot-01/RESULTS.md`](../../results/mechanism-20a-pilot-01/RESULTS.md).
This pilot validates the 10 candidate tasks before adding B and C. It is not a
test of the C-B effect.

## 1. Goal

Run **condition A only**, **10 candidate tasks**, **2 repeats** = **20 attempts**.

The pilot answers four questions:

1. Do the task images and verifiers work in Harbor?
2. Are the candidate strata plausible under condition A?
3. Do the tasks fit the token/time budget?
4. Are the F2P/P2P tests stable enough to freeze the 20-task set?

If the pilot passes, its A attempts can become the A arm for the 10 new tasks.
B and C would then be run later without rerunning A.

## 2. Design

| Item | Value |
|---|---|
| Experiment ID | `mechanism-20a-pilot-01` |
| Conditions | A only |
| Tasks | 10 candidates in `data/mechanism-20a-pilot-01/tasks.json` |
| Repeats | 2 per task |
| Attempts | 20 |
| Plan seed | `20261113` |
| Job prefix | `mechanism-20a` |
| Model | `deepseek-flash-1017` |
| Workflow | v2 (recorded, unused by A) |
| Benchmark | SWE-bench Pro V2 at `66f92766bba642462d4bbe5479e83f91f9211862` |
| Budgets | 80 steps, 1,000,000 cumulative tokens, 16,384 per response, 3,000 s |
| Verifier | Pro V2 task verifier, `shared` mode |

The frozen plan is `data/mechanism-20a-pilot-01/plan.json`. It contains 20
unique `(task_id, condition, repeat)` rows shuffled with the recorded seed.
The job prefix is different from `mechanism-v2`, so these jobs cannot collide
with the completed `mechanism-pilot-01` jobs.

### Candidate tasks

| Stratum | Task | Repo | Files / lines | F2P | P2P |
|---|---|---|---:|---:|---:|
| hard | `openlibrary-53d376` | OpenLibrary | 4 / 59 | 4 | 4 |
| hard | `qutebrowser-e70f5b` | qutebrowser | 2 / 46 | 7 | 36 |
| easy | `ansible-83fb24` | Ansible | 2 / 22 | 1 | 21 |
| easy | `openlibrary-43f9e7` | OpenLibrary | 1 / 29 | 1 | 60 |
| medium | `ansible-1c06c4` | Ansible | 4 / 71 | 4 | 21 |
| medium | `qutebrowser-5fdc83` | qutebrowser | 3 / 72 | 11 | 46 |
| ceiling | `ansible-e22e10` | Ansible | 2 / 30 | 4 | 26 |
| ceiling | `openlibrary-e80841` | OpenLibrary | 1 / 29 | 1 | 58 |
| floor | `openlibrary-25858f` | OpenLibrary | 4 / 419 | 13 | 33 |
| floor | `qutebrowser-ebfe9b` | qutebrowser | 2 / 314 | 12 | 55 |

Full task IDs are in `tasks.json`.

## 3. Pre-run checks

1. Confirm the Pro V2 checkout is at
   `66f92766bba642462d4bbe5479e83f91f9211862`.
2. Confirm the A condition, model profile, prompts, budgets, and verifier match
   `mechanism-pilot-01`.
3. Pre-pull the 10 task images using the plan, following
   `REPLICATION.md` section 5.
4. Run the dry run and confirm 20 `mechanism-20a-*` job names:

```bash
cd "$HARNESS_WSL"
python3 scripts/run_mechanism_wsl.py \
  --plan data/mechanism-20a-pilot-01/plan.json \
  --pro-dir "$PRO_WSL" \
  --dry-run
```

5. Record the code commit, model profile, Pro V2 commit, task checksums, image
   digests, and run window.

## 4. Run

```bash
cd "$HARNESS_WSL"
python3 scripts/run_mechanism_wsl.py \
  --plan data/mechanism-20a-pilot-01/plan.json \
  --pro-dir "$PRO_WSL" \
  --workers 2
```

Resume with `--start <next-order>`; do not rerun completed orders. Logs and
`run_status.jsonl` stay under `data/mechanism-20a-pilot-01/` and are gitignored.

After the run, extract the attempts:

```bash
python scripts/extract_behavior.py \
  --jobs "$PRO_WSL/jobs" \
  --pattern "mechanism-20a-*" \
  --dataset data/raw/swebench_pro_default.json \
  --out data/derived/mechanism-20a-pilot-01
```

The full `summarize_mechanism_run.py` expects A/B/C, so do not use it as the
pilot summary. Inspect `attempts.csv` directly or write a small A-only summary.

## 5. Pilot gates

Freeze the task set only if all of these hold:

- **Infrastructure:** 20/20 `rc=0`, no Harbor exceptions, no verifier crashes.
- **Provenance:** one checksum and image digest per task; no mid-run image
  changes.
- **Runtime:** no non-floor task exhausts both repeats on tokens or time.
  Budget exhaustion on a floor task is expected and must be reported separately.
- **Test stability:** F2P/P2P results are consistent enough that the task is not
  obviously flaky. A single 1/2 outcome is a flag, not automatic rejection.
- **Strata:** ceiling tasks should resolve 2/2; floor tasks should fail 0/2.
  If a ceiling task is 0/2 or a floor task is 2/2, reclassify it before freezing
  or replace it; do not leave a misleading stratum label.

Predefine the classification rule before inspecting results:

- 2/2 resolved -> ceiling
- 0/2 resolved -> floor
- 1/2 resolved -> mixed/intermediate

Do not use B/C outcomes to make any pilot decision.

## 6. Reuse rules

The pilot A attempts may be reused as the main A arm only if **all** of the
following are unchanged:

- the 10 task IDs and task bytes;
- the A condition implementation and prompts;
- the model profile and provider model string;
- budgets, Harbor version, verifier mode, and task images;
- the agent code path that affects condition A behavior.

If a task is replaced, its pilot A attempts are discarded; run A for the
replacement. If the A configuration or code changes, rerun A for every retained
task. If the DeepSeek provider build changes materially, treat the old A runs as
stale and record the change.

### Interleaving caveat

Reusing pilot A means A is run **before** B/C rather than interleaved with them.
That is a real design compromise: provider drift or machine load could confound
A versus B/C. Mitigations:

- run the B/C extension close in time to the pilot;
- record the provider model string and run windows;
- keep the original `mechanism-pilot-01` A runs as a separate reference;
- disclose the non-interleaved A arm in the results.

If strict interleaving is required, do not reuse the pilot A runs. Treat the
pilot as validation only and run a fresh 120-attempt (2-repeat) or 180-attempt
(3-repeat) plan.

## 7. Extension after a passing pilot

### Two repeats, exact reuse

- Existing `mechanism-pilot-01`: 60 attempts.
- New pilot A: 20 attempts (10 new tasks x A x 2).
- New B/C: 40 attempts (10 new tasks x B/C x 2).
- Total: **120 attempts** = 20 tasks x 3 conditions x 2 repeats.

### Three repeats

- Existing `mechanism-pilot-01`: 60 attempts.
- New pilot A: 20 attempts.
- New B/C at 2 repeats: 40 attempts.
- Third repeat for all 20 tasks x 3 conditions: 60 attempts.
- Total: **180 attempts** = 20 tasks x 3 conditions x 3 repeats.

Alternatively, run the new tasks at 3 repeats from the start and add only the
old tasks' third repeat: 20 pilot A + 60 new B/C (3 repeats) + 10 new A third
repeat + 30 old third repeats = 120 new attempts, total 180. The two routes are
equivalent; do not mix 2-repeat old tasks with 3-repeat new tasks in analysis.

## 8. Stop conditions

Do not proceed to B/C if:

- a task image or verifier is broken and cannot be fixed without changing the
  task;
- the task set changes after the pilot without rerunning A for replacements;
- the model profile or A condition changed after the pilot;
- the pilot reveals a systematic budget problem that makes the task
  uninformative.

In those cases, revise the task set or config, rerun the affected A attempts,
and freeze again before B/C.
