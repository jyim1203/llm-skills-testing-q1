# `main-local-01` -- main A/B/C run

- Date: 2026-10-24 (UTC), 09:05:01 to 14:15:58 (5h 11m wall time)
- Model: `local-qwen-sampling` (Qwen 3.5 9B Q4_K_M, `qwen3.5-9b-agent-64k`), temperature 0.2
- Budgets: 2,500,000 cumulative tokens, 16,384 per response, 80 steps, 1,800 s
- Tasks: 6 SWE-bench Lite instances; 5 repeats; 3 conditions; **90 attempts**
- Harness: 5.0.2; dataset revision `b0dde1093fe417d83b7184254edf8199c1f0dff5`
- Framework code at launch: `d3fbbd7` (the later `58046a3` commit only fixes the launcher/log path)
- Image lock: `data/image_locks/main-local-01.json`
- Log: `runs/logs/main-local-01.log`; artifacts: `runs/main-local-01/` (local, not committed)

## Result

**90/90 attempts completed, 0 infrastructure errors.** Grading finished cleanly:
**46 resolved / 44 unresolved**, 3,317 / 3,361 tests passed.

| Condition | Resolved | Rate | Mean tokens | Median tokens | Mean steps | Mean time |
|---|---:|---:|---:|---:|---:|---:|
| A baseline | 16/30 | 53.3% | 1,335,994 | 1,781,064 | 50.2 | 206 s |
| B prompt instructions | 15/30 | 50.0% | 1,485,612 | 1,432,447 | 59.1 | 193 s |
| C skill | 15/30 | 50.0% | 1,479,423 | 1,591,611 | 64.8 | 201 s |

Task-level paired effects (task-level bootstrap, 5,000 resamples):

- **B - A: -3.3 pp, 95% CI [-20.0, +10.0]**
- **C - A: -3.3 pp, 95% CI [-20.0, +10.0]**

On the 30 task/repeat pairs, B and A disagree on only 3 pairs (2 A-only, 1 B-only;
exact McNemar p = 1.0). C and A show the same discordant pattern. **B and C have
identical resolved/unresolved outcomes on all 30 paired attempts** (0 discordant pairs).

## Per-task breakdown

| Task | A baseline | B prompt | C skill |
|---|---|---|---|
| `django__django-11099` | 5/5 | 5/5 | 5/5 |
| `matplotlib__matplotlib-22835` | 0/5 | 0/5 | 0/5 |
| `psf__requests-3362` | 4/5 | 5/5 | 5/5 |
| `pytest-dev__pytest-5495` | 0/5 | 0/5 | 0/5 |
| `scikit-learn__scikit-learn-10297` | 5/5 | 5/5 | 5/5 |
| `sympy__sympy-20590` | 2/5 | 0/5 | 0/5 |
| **Total** | **16/30** | **15/30** | **15/30** |

Four of the six tasks are at ceiling or floor in every condition (60/90 attempts):
`django` and `scikit-learn` are 15/15; `matplotlib` and `pytest` are 0/15. The
only varying tasks are `requests` (A 4/5, B/C 5/5) and `sympy` (A 2/5, B/C 0/5).
The net -1 for B/C versus A is exactly those two tasks: +1 on `requests` and -2 on
`sympy`. B and C are indistinguishable at the attempt level.

## Skill use and cost

- C called `load_skill` in **30/30** attempts and discovered the skill in 30/30;
  A and B never loaded it. The skill changed behavior (more steps/tool calls), but
  not resolved outcomes relative to B.
- C averaged 64.8 steps and 64.3 tool calls per attempt, versus 59.1/58.9 for B
  and 50.2/49.7 for A. C did **not** buy a higher resolve rate.
### Per-task cost and gradability

Each cell has 5 attempts. **Non-empty** means the attempt produced a patch;
**gradable** means the harness returned test counts (`tests_total > 0` or
`tests_passed > 0`). Means are over all 5 attempts, including empty/ungradable
ones, so they reflect the cost of running that task/condition.

| Task | Cond | Non-empty | Gradable | Resolved | Mean tokens | Mean steps | Mean time (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| `django__django-11099` | A | 5 | 5 | 5 | 10,832 | 7.4 | 12.7 |
| | B | 5 | 5 | 5 | 422,904 | 33.0 | 70.5 |
| | C | 5 | 5 | 5 | 342,559 | 31.8 | 76.0 |
| `matplotlib__matplotlib-22835` | A | 5 | 5 | 0 | 1,929,324 | 80.0 | 245.2 |
| | B | 3 | 3 | 0 | 991,993 | 46.2 | 246.7 |
| | C | 4 | 4 | 0 | 1,740,128 | 67.6 | 224.7 |
| `psf__requests-3362` | A | 4 | 4 | 4 | 1,766,978 | 54.8 | 245.3 |
| | B | 5 | 5 | 5 | 2,251,911 | 70.8 | 206.3 |
| | C | 5 | 5 | 5 | 1,856,859 | 78.2 | 212.4 |
| `pytest-dev__pytest-5495` | A | 4 | 4 | 0 | 1,468,228 | 56.8 | 264.7 |
| | B | 4 | 3 | 0 | 1,852,605 | 78.0 | 226.4 |
| | C | 4 | 4 | 0 | 1,794,212 | 72.0 | 250.7 |
| `scikit-learn__scikit-learn-10297` | A | 5 | 5 | 5 | 2,026,783 | 61.4 | 152.4 |
| | B | 5 | 5 | 5 | 2,170,298 | 55.8 | 149.9 |
| | C | 5 | 5 | 5 | 1,919,233 | 63.4 | 162.3 |
| `sympy__sympy-20590` | A | 5 | 5 | 2 | 813,819 | 40.8 | 313.9 |
| | B | 3 | 3 | 0 | 1,223,959 | 71.0 | 255.8 |
| | C | 4 | 4 | 0 | 1,223,549 | 75.6 | 278.6 |
| **All tasks** | **A** | **28** | **28** | **16** | **1,335,994** | **50.2** | **205.7** |
| | **B** | **25** | **24** | **15** | **1,485,611** | **59.1** | **192.6** |
| | **C** | **27** | **27** | **15** | **1,479,423** | **64.8** | **200.8** |
| | **All** | **80** | **79** | **46** | **1,433,676** | **58.0** | **199.7** |

The one gap between non-empty and gradable is `pytest__pytest-5495` / B /
attempt 2: the patch was non-empty but the harness returned 0 tests
(`tests_failed`, 0/0), so it is unresolved but not counted as gradable.

Two patterns stand out. On `django`, all conditions resolve 5/5, but A spends
only 10.8k tokens and 7.4 steps while B/C spend 343k-423k tokens and ~32 steps.
On `requests`, B/C gain one resolution over A (4/5 to 5/5), but B costs 2.25M
tokens and 70.8 steps on average. `sympy` is the only task where A beats B/C
(2/5 versus 0/5), and B/C are much more expensive there.

### Termination outcomes

| Outcome | A | B | C | Total |
|---|---:|---:|---:|---:|
| Natural finish (`stop`) | 8 | 8 | 10 | 26 |
| Cumulative token budget (`token_budget`, 2.5M) | 5 | 5 | 1 | 11 |
| Per-response length (`length`, 16,384) | 9 | 6 | 5 | 20 |
| Step limit (`max_steps`, 80) | 8 | 11 | 14 | 33 |
| Time limit (1,800 s) | 0 | 0 | 0 | 0 |
| Infrastructure error | 0 | 0 | 0 | 0 |
| **Total** | **30** | **30** | **30** | **90** |

All 90 attempts reached a terminal state. The time limit never bound (maximum
observed attempt was 438 s). One additional A/`scikit-learn` attempt finished
naturally at 2,545,359 tokens, just over the 2.5M cap; the 11 `token_budget`
stops are the attempts the budget actually terminated.

| Outcome | n | Resolved | Unresolved | Empty patch |
|---|---:|---:|---:|---:|
| Natural finish | 26 | 24 | 2 | 0 |
| Step limit | 33 | 7 | 26 | 3 |
| Token budget | 11 | 10 | 1 | 0 |
| Response length | 20 | 5 | 15 | 7 |
| Time limit | 0 | 0 | 0 | 0 |
| **Total** | **90** | **46** | **44** | **10** |

Empty-patch counts overlap the outcome rows; all 10 occur in step-limit or
response-length stops. Empty-patch attempts are unresolved without a harness
grade, so compare resolved status rather than raw test totals.
- Total agent time was 4.99 h; total tokens were 129,030,867. Wall time including
  grading was 5h 11m.

## Interpretation

This run does **not** detect an effect of the prompt instructions or the skill.
The point estimates are slightly negative (-3.3 pp for both B and C), the 95%
intervals are wide and include zero, and B and C are outcome-identical. This is a
null result at this sample size, not evidence that prompts/skills cannot help.

The design is underpowered for the question: 30 attempts per condition, but only
30 of the 90 attempts are on tasks that discriminate at all, and the 5 repeats are
clustered within tasks. A difference of 1-2 attempts is noise. The earlier local
pilot (A 3/6, B 3/6, C 4/6, 1.5M/8k budgets) is **not pooled** with this run and
does not confirm a C advantage.

## Caveats

- 5 repeats x 6 tasks per condition; task-level bootstrap with only 6 tasks.
- Two ceiling tasks and two floor tasks consume 60/90 attempts; effective
  discrimination is concentrated in `requests` and `sympy`.
- The planner randomizes condition order per task but runs each condition's five
  repeats as a block, so condition blocks are not strictly interleaved by repeat;
  repeat-level results were stable, but time drift is not fully controlled.
- The 80-step cap (33 stops), 16,384 response cap (20 `length` stops), and 2.5M
  token cap (11 stops) were all binding; cost comparisons are descriptive.
- `runs.jsonl` leaves `resolved` null; `evaluation_status` is the authoritative
  outcome field.
- `pilot-01` is frozen and is not pooled with this run.
