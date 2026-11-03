# Verified Pilot 01 - Calibration Results

**Status:** operational pass; scientific ceiling warning.

**Run:** `runs/verified-pilot-01`  
**Model:** DeepSeek V4.1 Flash 1017, thinking enabled, `reasoning_effort=medium`  
**Design:** 10 tasks x 3 conditions x 1 repeat = 30 attempts, 2 workers  
**Harness:** official `swebench==5.0.2`  
**Image lock:** `data/image_locks/verified-pilot-01.json`

This is a calibration run, not a reported condition effect. One repeat cannot
estimate between-repeat variance or support a condition inference.

## Operational result

| Metric | Value |
|---|---:|
| Attempts completed | 30 / 30 |
| Infrastructure errors | 0 |
| Graded attempts | 30 |
| Resolved | 29 |
| Unresolved | 1 |
| Tests passed | 3,641 / 3,642 |
| C skill loaded | 10 / 10 |
| A/B skill loaded | 0 / 10 |
| Mean elapsed per attempt | 74 s |
| Max elapsed | 170 s |
| First-to-last attempt start | 17.7 min |
| Total tokens | 12,321,695 |
| Input / output tokens | 12,142,317 / 179,378 |
| Mean tokens per attempt | 410,723 |
| Max steps | 39 |
| Stop reasons | 28 `stop`, 2 `token_budget`, 0 `length` |

The two token-budget stops were both A-baseline attempts (Django and Sphinx) and
both still resolved. No image or container failures occurred.

## By condition

| Condition | Resolved | Rate | Mean tokens | Mean seconds | Mean steps |
|---|---:|---:|---:|---:|---:|
| A baseline | 10 / 10 | 1.00 | 445,789 | 68 | 23.3 |
| B prompt instructions | 10 / 10 | 1.00 | 329,228 | 63 | 19.1 |
| C skill | 9 / 10 | 0.90 | 457,152 | 91 | 27.0 |

The token differences are descriptive only. With one repeat and a near-ceiling
outcome, they are not condition effects.

## Per-task outcomes

| Task | A | B | C | C note |
|---|---|---|---|---|
| `pallets__flask-5014` | resolved | resolved | resolved | |
| `psf__requests-5414` | resolved | resolved | resolved | |
| `astropy__astropy-13033` | resolved | resolved | resolved | |
| `mwaskom__seaborn-3187` | resolved | resolved | resolved | |
| `scikit-learn__scikit-learn-12973` | resolved | resolved | **unresolved** | failed `test_lasso_lars_fit_copyX_behaviour[False]` |
| `django__django-15957` | resolved | resolved | resolved | A hit token cap |
| `sympy__sympy-14248` | resolved | resolved | resolved | |
| `pytest-dev__pytest-6197` | resolved | resolved | resolved | |
| `pylint-dev__pylint-8898` | resolved | resolved | resolved | |
| `sphinx-doc__sphinx-7590` | resolved | resolved | resolved | A hit token cap |

The single C failure was a near miss: C changed the `fit` signature and default
but did not pass the local `copy_X` through to `_preprocess_data`, so
`copy_X=False` still did not overwrite `X`. A and B made the complete change.

## Interpretation

**Operational success:** the full pipeline works end to end with two workers,
thinking enabled, reasoning-content round-tripping, all ten Docker images, and
official grading.

**Scientific warning:** the pilot is near ceiling. All A and B attempts resolved;
only one C attempt failed. Five hard-stratum tasks and the `>4h` Sphinx task were
solved by every condition. With eight repeats, the main run may produce mostly
8/8 cells and very little resolution variance for A/B, which would make the
primary C-vs-B contrast weakly informative.

This could reflect a strong model, public-benchmark contamination, or both. The
pilot cannot separate those explanations.

The main run is computationally cheap: at the observed mean, 240 attempts is
about 98.6M tokens, roughly 2.4 hours of worker time at two workers, plus
grading. The problem is information, not wall time.

## Decision before the 240-attempt run

Do not launch unchanged if resolution on this task set is the primary outcome.

Options:

1. **Run unchanged anyway.** Useful mainly as a cost/process study (tokens,
   steps, skill-load overhead), not as a sensitive resolution comparison.
2. **Freeze a harder task set before the main run.** Treat the pilot as
   calibration, disclose the change, and select tasks with more complex patches
   or lower expected solve rates. This is outcome-aware selection and must not
   be presented as pre-registered.
3. **Tighten the budget** (for example 250k-400k cumulative tokens or 40 steps)
   to create a harder regime. This changes the construct and creates cap-bound
   outcomes.
4. **Use fresh/private tasks** for a clean generalization claim.
5. **Keep thinking on but add a repeatability micro-check** before deciding
   whether 8 repeats add information.

Recommendation: pause before the 240-attempt run, decide between option 1 and
option 2, and record the decision before looking at any main-run outcomes.
