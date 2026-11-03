# Frozen Task Set — Mechanism Pilot 01

**Status:** frozen 2026-11-03

**Workflow:** v2 canonical (`workflow_instructions_v2.md`)

**Selection rule:** pilot ceiling/floor anchors + static difficulty mix; no B/C outcomes used.

## The 10 tasks

| # | Stratum | Repo | Task ID | Files / changed lines | F2P | P2P |
|---:|---|---|---|---:|---:|---:|
| 1 | Ceiling | ansible/ansible | `instance_ansible__ansible-e9e6001263f51103e96e58ad382660df0f3d0e39-v30a923fb5c164d6cd18280c02422f75e611e8fb2` | 2 / 96 | 8 | 20 |
| 2 | Ceiling | qutebrowser/qutebrowser | `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058defd15aabb24617a76402-v5fc38aaf22415ab0b70567368332beee7955b367` | 1 / 59 | 1869 | 0 |
| 3 | Floor (known) | internetarchive/openlibrary | `instance_internetarchive__openlibrary-0dc5b20fa186f9714f8a838178597e69f549d026-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59` | 1 / 62 | 6 | 55 |
| 4 | Floor (expected) | internetarchive/openlibrary | `instance_internetarchive__openlibrary-b67138b316b1e9c11df8a4a8391fe5cc8e75ff9f-ve8c8d62a2b60610a3c4631f5f23ed866bada9818` | 6 / 888 | 11 | 53 |
| 5 | New — easy | qutebrowser/qutebrowser | `instance_qutebrowser__qutebrowser-96b997802e942937e81d2b8a32d08f00d3f4bc4e-v5fc38aaf22415ab0b70567368332beee7955b367` | 2 / 24 | 17 | 161 |
| 6 | New — easy | ansible/ansible | `instance_ansible__ansible-12734fa21c08a0ce8c84e533abdc560db2eb1955-v7eee2454f617569fd6889f2211f75bc02a35f9f8` | 3 / 26 | 1 | 4 |
| 7 | New — medium | internetarchive/openlibrary | `instance_internetarchive__openlibrary-d8162c226a9d576f094dc1830c4c1ffd0be2dd17-v76304ecdb3a5954fcf13feb710e8c40fcf24b73c` | 3 / 74 | 18 | 0 |
| 8 | New — medium | ansible/ansible | `instance_ansible__ansible-5e369604e1930b1a2e071fecd7ec5276ebd12cb1-v0f01c69f1e2528b935359cfe578530722bca2c59` | 5 / 94 | 7 | 2 |
| 9 | New — hard | ansible/ansible | `instance_ansible__ansible-d62496fe416623e88b90139dc7917080cb04ce70-v0f01c69f1e2528b935359cfe578530722bca2c59` | 3 / 35 | 22 | 92 |
| 10 | New — hard | qutebrowser/qutebrowser | `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af574386e277dd2388d094-v2ef375ac784985212b1805e1d0431dc8f1b3c171` | 4 / 45 | 5 | 100 |

## Composition

- Repos: **ansible 4, openlibrary 3, qutebrowser 3**
- Strata: **2 ceiling, 2 floor, 2 easy, 2 medium, 2 hard**
- Conditions: A, B, C
- Repeats: 2
- Total attempts: **60**

## Notes

- `openlibrary-0dc5b2` is the known pilot floor: all conditions hit the 1M cap.
- `openlibrary-b67138` is the `hard_largest` task; floor status is expected from
  its 888-line cross-file churn, not measured.
- `qutebrowser-3e21c8` and `openlibrary-d8162c` have P2P=0; outcome is F2P-only
  for those tasks.
- The alternative for `b67138`, if runtime is too high, is
  `instance_internetarchive__openlibrary-630221ab686c64e75a2ce253c893c033e4814b2e-v93c53c13d5f9b383ebb411ee7750b49dcd1a34c6`
  (6 files / 328 lines, F2P 9, P2P 0). Swapping is allowed only before the run.

## Freeze checklist

- [x] 2 ceiling IDs
- [x] 2 floor IDs
- [x] 6 new IDs
- [x] all three repos represented
- [ ] image digest per task recorded after pull
- [ ] task checksum per task recorded after freeze
- [x] no replacement after B/C outcomes
- [ ] randomized 60-attempt execution order recorded with seed
