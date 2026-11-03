# Behavior / Efficiency Analysis Plan

## Unit of analysis

The independent unit is the **task**, not the attempt. Each task-condition has 2
repeats. Average the repeats first, then compare tasks:

```text
attempt -> task-condition mean -> paired task difference -> aggregate
```

This prevents 2 repeats from being treated as 2 independent tasks.

## Contrasts

| Contrast | Interpretation |
|---|---|
| C − B | delivery mechanism, identical content |
| B − A | content as prompt |
| C − A | content as skill |

C − B is the primary contrast. B − A and C − A are secondary.

## Primary endpoints

### P1 — Test-before-edit rate

Per attempt:

```text
1 if any test invocation occurs before the first edit else 0
```

This is direct workflow adherence. The pilot A baseline was 0/3, so it has room
to vary. Report per-task proportions and paired task differences, plus raw
counts (improved / worsened / tied).

### P2 — Read/search-before-edit rate

Per attempt:

```text
1 if any read/search/list action occurs before the first edit else 0
```

This measures search discipline. The pilot A baseline was 2/3, so it is not at
ceiling. If A is at ceiling in the frozen set, report that explicitly.

### P3 — Time to first edit

Seconds from `run_start` to the first edit event. If `events.jsonl` is absent,
use the first-edit event index as a fallback and label it as such.

### P4 — Total tokens per attempt

`input_tokens + output_tokens` from provider usage. Report median and mean;
tokens are right-skewed.

## Secondary endpoints

- **post-edit verification rate** — A was 3/3 in the pilot; treat as a
  ceiling/treatment check, not a primary effect
- test-call count, test-to-edit ratio, verification intensity
- tool mix and tool-transition counts
- unique files read/edited, patch files/lines
- repeated commands, tool errors, unknown tools
- wall time, model latency, tool duration
- budget exhaustion rate
- resolved, F2P fraction, P2P fraction
- tokens per resolved task, steps per resolved task

## Summary statistics

For each condition and endpoint:

- attempts, tasks
- mean, median, standard deviation
- min/max
- missing count
- for binary endpoints: successes / denominator

## Paired effects

For each contrast and task:

```text
d_t = mean(condition metric for task t) - mean(reference metric for task t)
```

Then:

- mean and median of `d_t`
- bootstrap 95% CI over tasks (resample tasks with replacement, 5,000 draws)
- sign test / exact binomial for direction
- Cliff's delta or rank-biserial for effect size
- report `n_tasks` and the number of discordant tasks

With 10 tasks this is descriptive. Do not describe a p-value as a definitive
causal test.

## Mixed model (optional)

For continuous endpoints:

```text
metric ~ condition + stratum + (1 | task)
```

Report condition coefficients and confidence intervals. Label the model as
descriptive because there are only 10 task groups. Do not use the model to
rescue a null result.

## Stratification

Analyze at least:

- ceiling tasks (A resolved in pilot)
- floor/budget-limited tasks
- new/intermediate tasks

If conditions differ only on one stratum, say so. Do not pool the strata into a
single average without showing the breakdown.

## Censoring

Budget exhaustion is a separate state:

- keep `budget_exhausted` as an endpoint
- for outcome, report “resolved within budget”
- do not recode exhaustion as a normal unresolved attempt without labeling it

## Missing data

- missing `events.jsonl`: event-only metrics are null; message-derived metrics
  remain available
- missing verifier output: outcome is null, not false
- infrastructure/API/verifier exception: excluded from primary endpoints and
  reported separately

## Tables and plots

1. Task × condition table for P1–P4.
2. Paired dumbbell plot for each primary endpoint.
3. Token distribution by condition (log scale).
4. Tool-mix stacked bars by condition.
5. Tool-transition heatmap or top transitions by condition.
6. Verification heatmap: task × condition.
7. Budget-exhaustion and error counts.
8. Case-study table: 2–3 traces per condition with failure mode and adherence.

## Qualitative coding

Predefine codes before reading traces:

- wrong file / wrong layer
- incomplete fix (missed parallel path or edge case)
- regression in adjacent behavior
- no verification
- verification only after failure
- tool misuse / environment confusion
- budget exhaustion
- correct fix with inefficient exploration

Sample 2–3 traces per condition, balanced by task and outcome. Report agreement
or label the coding as descriptive.

## Interpretation rules

- Treat outcome as exploratory.
- A null result on P1–P4 is informative only if the manipulation check passed
  (C loaded the skill; B received the full text) and the task strata had room to
  vary.
- Do not claim “skills don’t help” from 10 tasks.
- Do not claim “skills help” from a small task-level difference without showing
  the paired distribution.
