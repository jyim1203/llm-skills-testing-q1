# Statistical Analysis: Final DeepSeek 20-Task Experiment

**Scope:** this section applies only to the final combined DeepSeek experiment:
20 tasks x 3 conditions x 2 repeats = 120 attempts.

**Status:** exploratory analysis of the frozen 20-task set. The task set was
fixed before this analysis, but the statistical plan was specified after the run
and was not preregistered.

## 1. Analysis set and unit

The unit of analysis is the **task**, not the attempt. For task \(t\), condition
\(c \in \{A,B,C\}\), and repeat \(r \in \{1,2\}\), let \(Y_{tcr}\) be the
outcome. The task-condition mean is

\[
\bar{Y}_{tc} = \frac{1}{2}\sum_{r=1}^{2} Y_{tcr}.
\]

The paired condition difference for task \(t\) is

\[
\Delta_t = \bar{Y}_{tC} - \bar{Y}_{tB},
\]

and the estimand is the mean paired difference

\[
\Delta = \frac{1}{n}\sum_{t=1}^{n}\Delta_t,
\qquad n=20.
\]

Repeats are provider draws, not independent samples. Averaging within task
first avoids treating the 120 attempts as independent observations. No
attempt-level pooling is used in the primary analysis.

## 2. Endpoints and hypotheses

The primary outcome is **resolved** under the primary contrast **C - B**.

Secondary outcomes for C - B are:

- test calls
- steps
- total tokens
- time to first edit
- post-edit verification
- F2P fraction
- P2P fraction
- budget exhaustion

`test_before_edit` and `read_before_edit` are reported descriptively because
they are saturated or near-floor. `time_to_first_edit` is defined for 19 tasks;
`P2P` is defined for 17 tasks. Tasks without an edit or without P2P tests are
excluded only from those endpoint-specific paired analyses.

Secondary contrasts are B - A and C - A. These are reported descriptively
because the new-task A runs were not interleaved with B/C.

All tests are two-sided with \(\alpha = 0.05\).

## 3. Primary test

For C - B resolved, use a **paired sign-flip permutation test**:

1. Compute the 20 observed task-level differences \(\Delta_t\).
2. Randomly flip the sign of each \(\Delta_t\) with probability 0.5.
3. Recompute the mean difference.
4. Repeat 100,000 times and compute a two-sided p-value.

This test is exact in structure for paired data and does not assume normality.
Because task-level resolved means take values in \(\{0, 0.5, 1\}\), the test has
limited resolution with \(n=20\).

The 95% confidence interval is a **task-level percentile bootstrap**:

- resample the 20 tasks with replacement;
- compute the mean paired difference in each resample;
- repeat 10,000 times;
- take the 2.5th and 97.5th percentiles.

Effect sizes are the mean risk difference, paired Cohen's \(d_z\), and the
matched-pairs rank-biserial correlation.

## 4. Secondary tests

For continuous or count-like endpoints, use:

- paired Wilcoxon signed-rank test;
- paired sign-flip permutation test as a robustness check;
- task-level percentile bootstrap confidence interval;
- paired Cohen's \(d_z\);
- matched-pairs rank-biserial correlation.

For binary endpoints, use the sign-flip permutation test and sign test rather
than Wilcoxon.

Multiplicity is controlled with **Holm-Bonferroni** across the 10 C - B
secondary endpoints. The primary endpoint is not included in that family.

## 5. Results

### 5.1 Primary endpoint: C - B resolved

| Quantity | Estimate |
|---|---:|
| Mean difference | **-0.100** |
| 95% bootstrap CI | **[-0.225, +0.025]** |
| Sign-flip permutation p | **0.313** |
| Exact sign-test p | **0.375** |
| Tasks: C better / C worse / tie | **1 / 4 / 15** |
| Paired Cohen's \(d_z\) | **-0.325** |
| Rank-biserial | **-0.667** |

The primary result is directionally negative but statistically uncertain. The
confidence interval includes zero, and only five of 20 tasks are discordant.

### 5.2 Secondary endpoints: C - B

| Endpoint | n pairs | Mean diff | 95% CI | Perm. p | Wilcoxon p | Holm p | \(d_z\) |
|---|---:|---:|---|---:|---:|---:|---:|
| Test calls | 20 | **+1.60** | [+0.55, +2.83] | **0.008** | **0.014** | 0.085 | **0.603** |
| Steps | 20 | **+3.15** | [+1.05, +5.35] | **0.013** | **0.018** | 0.119 | **0.617** |
| Total tokens | 20 | +807 | [-48,506, +55,267] | 0.978 | 0.674 | 1.000 | 0.007 |
| Time to first edit | 19 | -2.67 s | [-14.30, +7.59] | 0.657 | 0.829 | 1.000 | -0.107 |
| Post-edit verification | 20 | -0.075 | [-0.200, +0.050] | 0.455 | 0.257 | 1.000 | -0.255 |
| F2P fraction | 20 | -0.042 | [-0.129, +0.045] | 0.407 | 0.352 | 1.000 | -0.209 |
| P2P fraction | 17 | -0.028 | [-0.085, 0.000] | 1.000 | 0.317 | 1.000 | -0.243 |
| Budget exhaustion | 20 | -0.100 | [-0.225, +0.025] | 0.289 | — | 1.000 | -0.325 |
| Test-before-edit | 20 | 0.000 | [-0.100, +0.100] | 1.000 | — | 1.000 | 0.000 |
| Read-before-edit | 20 | +0.075 | [0.000, +0.200] | 0.502 | — | 1.000 | 0.307 |

The strongest unadjusted secondary signals are **more test calls** and **more
steps** under C. Neither survives Holm correction across the 10 secondary
endpoints. C - B total tokens are essentially null.

### 5.3 Secondary contrasts

| Contrast | Endpoint | Mean diff | 95% CI | Perm. p | Wilcoxon p |
|---|---|---:|---|---:|---:|
| B - A | Resolved | +0.075 | [-0.050, +0.200] | 0.500 | — |
| B - A | Test calls | -0.725 | [-1.275, -0.200] | 0.026 | 0.027 |
| B - A | Steps | -1.875 | [-3.500, -0.250] | 0.045 | 0.049 |
| B - A | Total tokens | -29,989 | [-80,081, +22,154] | 0.282 | 0.277 |
| B - A | Time to first edit | +8.35 s | [-2.37, +20.12] | 0.176 | 0.275 |
| B - A | Post-edit verification | -0.050 | [-0.200, +0.100] | 0.766 | 0.527 |
| C - A | Resolved | -0.025 | [-0.175, +0.125] | 1.000 | — |
| C - A | Test calls | +0.875 | [0.000, +1.950] | 0.116 | 0.184 |
| C - A | Steps | +1.275 | [-0.225, +2.875] | 0.141 | 0.122 |
| C - A | Total tokens | -29,183 | [-66,635, +8,546] | 0.155 | 0.070 |
| C - A | Time to first edit | +5.95 s | [-3.40, +15.26] | 0.242 | 0.189 |
| C - A | Post-edit verification | -0.125 | [-0.325, +0.075] | 0.341 | 0.218 |

B is leaner than A on test calls and steps. C - A is mostly null. These contrasts
are unadjusted and descriptive because of the non-interleaved A arm for the new
tasks.

## 6. Sensitivity analyses

C - B resolved under alternative task subsets:

| Analysis set | Tasks | Mean C - B | Perm. p | W/L/T |
|---|---:|---:|---:|---:|
| All tasks | 20 | -0.100 | 0.313 | 1/4/15 |
| Exclude ceiling and floor | 13 | -0.154 | 0.313 | 1/4/8 |
| Medium + hard only | 9 | -0.222 | 0.313 | 1/4/4 |
| Original 10 tasks | 10 | -0.200 | 0.250 | 0/3/7 |
| New 10 tasks | 10 | 0.000 | — | 1/1/8 |

The C - B resolved deficit is concentrated in the original 10 tasks; the new 10
tasks are exactly balanced between B and C. This is consistent with the
task-level pattern, where five tasks account for the entire net difference.

## 7. Interpretation

- The primary C - B resolved effect is negative but not statistically
  distinguishable from zero.
- C is behaviorally heavier: it makes more test calls and takes more steps. These
  are the strongest unadjusted secondary effects, but they do not survive Holm
  correction across the secondary family.
- C does not show a resolved-rate advantage. Its point estimate is lower than B,
  and the only clear behavioral signal is increased verification activity.
- The C deficit is not uniform: ceiling and easy strata are saturated, the
  medium stratum carries most of the negative resolved difference, and the new
  10 tasks show no net C - B resolved difference.
- B is the leanest condition on steps and test calls, and has the highest
  resolved point estimate, but the B - A resolved difference is also uncertain.
- These results are descriptive. The task set is not perfectly balanced
  (3 floor, 5 hard), the new-task A arm is non-interleaved, and the provider
  exposes no sampling seed.

## 8. What not to infer

- Do not interpret the 120 attempts as 120 independent observations.
- Do not use attempt-level McNemar as the primary test; repeats are clustered
  within task.
- Do not claim a confirmatory C - B effect from \(n=20\) tasks.
- Do not interpret the unadjusted test-call and step p-values as surviving
  multiple-comparison correction.
- Do not compare stratum-specific p-values as if each stratum were a separate
  powered experiment.

## 9. Reproducibility

- Analysis script: `scripts/statistical_analysis_mechanism_20.py`
- Machine-readable results:
  `results/mechanism-20-combined/statistical_analysis.json`
- Combined task-level data:
  `data/derived/mechanism-20-combined/attempts.json`
- Bootstrap resamples: 10,000
- Sign-flip permutations: 100,000
- Random seed: `20261116`
