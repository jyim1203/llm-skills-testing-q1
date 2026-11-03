# Task Selection (Draft — Not Frozen)

The mechanism study needs **10 Python tasks** across the three Pro V2 Python
repositories:

- `ansible/ansible`
- `internetarchive/openlibrary`
- `qutebrowser/qutebrowser`

Because Pro V2 has only three Python repositories, multiple tasks per repo are
allowed. Selection is based on condition-A evidence and static task properties,
not on B/C outcomes.

## Strata

| Stratum | Count | Rule |
|---|---:|---|
| Ceiling | 2 | Resolved by A in the pilot |
| Floor / budget-limited | 2 | A exhausted the 1M budget or produced an empty patch |
| New / intermediate | 6 | Static variety in repo, patch size, test count, `hard` |

## Known anchors

| Task | Repo | Stratum | Evidence |
|---|---|---|---|
| `instance_ansible__ansible-e9e6001263f51103e96e58ad382660df0f3d0e39-v30a923fb5c164d6cd18280c02422f75e611e8fb2` | ansible/ansible | Ceiling | A/B/C resolved in pilot |
| `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058defd15aabb24617a76402-v5fc38aaf22415ab0b70567368332beee7955b367` | qutebrowser/qutebrowser | Ceiling | A/B/C resolved in pilot |
| `instance_internetarchive__openlibrary-0dc5b20fa186f9714f8a838178597e69f549d026-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59` | internetarchive/openlibrary | Floor | A/B/C hit 1M token budget; all unresolved |

The second floor task is **TBD**; choose a task with high static complexity or
prior evidence of budget exhaustion, not because a condition failed it.

## New-task selection

1. Start from the 237 Python rows in the Pro V2 dataset.
2. Exclude the three anchors above.
3. Prefer tasks with:
   - a clear fail-to-pass test set,
   - a moderate patch size,
   - at least one test file,
   - repo diversity.
4. Avoid selecting only tiny patches (too easy) or only enormous patches
   (budget floor).
5. Record the final 10 IDs, image digests, task checksums, and strata here
   before launching the mechanism run.

## Freeze checklist

- [ ] 2 ceiling IDs
- [ ] 2 floor IDs
- [ ] 6 new IDs
- [ ] one or more tasks from each of the three repos
- [ ] image digest per task
- [ ] task checksum per task
- [ ] no replacement after seeing B/C outcomes
- [ ] randomized 60-attempt execution order recorded with its seed

## Dataset fields used

The local Pro V2 dataset (`data/raw/swebench_pro_default.json`, ignored) carries:

- `repo`, `repo_language`, `hard`
- `patch`, `test_patch`
- `fail_to_pass`, `pass_to_pass` (JSON-encoded strings)
- `problem_statement`, `requirements`
- `docker_image`
- `before_repo_set_cmd`, `selected_test_files_to_run`

These are used for stratification and for F2P/P2P scoring, not for task hints.
