# V3 Skill Content Audit (Optional — Not Used in This Run)

**Status:** deferred. The mechanism run uses the canonical v2 workflow. This
audit would only be needed if v3 becomes a separate content arm.

Purpose: check whether V3 contains information beyond generic model priors. This
is a manipulation check, not a condition outcome. Do not change the primary
endpoints after reading it.

## Instructions to classify

For each V3 section/rule, mark:

- **G** — generic prior (a strong model likely already does this)
- **P** — Python-repository-specific procedure
- **N** — non-obvious/actionable (a concrete discovery or decision rule)

| V3 item | G/P/N | Notes |
|---|---|---|
| Turn report into testable target | | |
| Use exact error text / option names as spec | | |
| Read tests and conftest before broad code | | |
| Discover repository-native test command | | |
| Prefer narrow test node | | |
| Fix test harness/import errors before logic | | |
| Read sibling implementation / conventions | | |
| Use git history for regressions | | |
| State root cause and smallest observable change | | |
| Update parallel code paths consistently | | |
| Check None/empty/bool/mutable-default/encoding/exception edge cases | | |
| Verify narrow → module → adjacent tests | | |
| Inspect diff for test edits/debug prints/unrelated changes | | |
| Budget rule: hypothesis + patch by ~40% | | |
| Stop after clean narrow/module tests | | |
| Report requested vs actual verification | | |

## Summary

- Approximate share G / P / N:
- Strongest non-generic rules:
- Rules likely already saturated in A:
- Decision: proceed / strengthen V3 / reframe as delivery-only / stop

## Baseline adherence input

See `PILOT_BASELINE.md`. Condition A already:

- ran a post-edit test in 3/3 pilot tasks;
- ran a pre-edit test in 0/3;
- read/searched before editing in 2/3.

Use this to avoid treating saturated behaviors as treatment effects.
