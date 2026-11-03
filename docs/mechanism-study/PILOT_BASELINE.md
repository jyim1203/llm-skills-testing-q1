# Pilot Baseline Adherence (Read-Only)

Computed from the existing `harbor-pilot-01` logs with
`scripts/extract_behavior.py`. These are **3 tasks, 1 repeat, condition A only**.
They are descriptive and are not a condition comparison.

## Condition A behavior

| Task | Resolved | Steps | Tool calls | Test calls | Read calls | Search calls | Edit calls | Read before edit | Test before edit | Post-edit test | F2P | P2P |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|
| Ansible `e9e600` | yes | 11 | 13 | 1 | 7 | 4 | 2 | no | no | yes | 8/8 | 20/20 |
| qutebrowser `3e21c8` | yes | 26 | 28 | 4 | 8 | 4 | 4 | yes | no | yes | 1869/1869 | 0/0 |
| OpenLibrary `0dc5b2` | no | 25 | 33 | 2 | 13 | 8 | 5 | yes | no | yes | 6/6 | 53/55 |

Additional observations:

- All three A attempts ran at least one test after their last edit
  (`verification_rate = 1.0`). **Post-edit verification is at ceiling for A in
  this pilot.**
- None of the three A attempts ran a test before the first edit
  (`test_before_edit = 0/3`).
- Two of three read/search before editing (`read_before_edit = 2/3`).
- The two non-Ansible tasks hit the 1M-token cap; qutebrowser still resolved.
- OpenLibrary passed all 6 fail-to-pass tests but failed 2 pass-to-pass tests
  (plus 2 additional verifier failures), so reward was 0. This is why a graded
  F2P/P2P view is useful.

## Implications for endpoints

Because post-edit verification is already saturated in A:

- Keep **post-edit verification** as a secondary/treatment-check endpoint, not
  the primary behavioral endpoint.
- Use **test-before-edit** as a direct adherence endpoint: A is at 0/3.
- Use **read/search-before-edit** as a search-discipline endpoint: A is at 2/3.
- Use **time to first edit** and **tokens per attempt** as pacing/efficiency
  endpoints.

This does not mean “more test-before-edit is better.” It means the endpoint has
room to vary and directly reflects the workflow text.

## Caveats

- Three tasks, one repeat; not an effect estimate.
- The old pilot has no `events.jsonl`, so event timestamps are unavailable.
- Shell edit/test classification is heuristic.
- `test_before_edit` is a binary summary; a future analysis should also report
  the exact command and test target.
