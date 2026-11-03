# Harbor / SWE-Bench Pro V2 Pilot

**Status:** Harbor integration smoke pilot complete. This is not the full
10-task pilot and is not a condition-effect result.

## Setup

| Item | Value |
|---|---|
| Benchmark | SWE-Bench Pro V2, HARD-51 tasks |
| Pro repo commit | `66f92766bba642462d4bbe5479e83f91f9211862` |
| Harbor | `0.25.0`, local Docker |
| Agent | `skills_experiment.harbor_agent:HarborSkillsAgent` |
| Conditions | A baseline, B prompt instructions, C skill |
| Tasks | 3, one from each Python repository |
| Attempts | 3 tasks x 3 conditions x 1 repeat = 9 |
| Agent budget | 80 steps, 1M cumulative tokens, 3000 s |
| Grading | Pro V2 `tests/test.sh` verifier |

Tasks:

- `instance_ansible__ansible-e9e600...` (`ansible/ansible`)
- `instance_internetarchive__openlibrary-0dc5b20...` (`internetarchive/openlibrary`)
- `instance_qutebrowser__qutebrowser-3e21c821...` (`qutebrowser/qutebrowser`)

Oracle and empty-patch checks were run on the OpenLibrary task first:

- oracle: 1/1 resolved
- nop: 0/1 resolved

## Result

| Condition | Resolved | Rate | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| A baseline | 2 / 3 | 0.67 | 2,202,002 | 52,637 |
| B prompt | 2 / 3 | 0.67 | 2,343,926 | 54,675 |
| C skill | 2 / 3 | 0.67 | 2,306,425 | 52,315 |

Per task:

| Task | A | B | C |
|---|---|---|---|
| Ansible hard task | resolved | resolved | resolved |
| OpenLibrary hard task | unresolved | unresolved | unresolved |
| qutebrowser hard task | resolved | resolved | resolved |

All 9 trials completed with **0 exceptions** and no infrastructure errors.

## Integration checks

- A system prompt: 228 chars
- B system prompt: 2,106 chars
- C system prompt: 711 chars
- C `load_skill`: **3/3**
- A/B `load_skill`: **0/3**
- C loaded skill body hash:
  `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`
- All patches were captured by the agent; the only empty patch was C on
  OpenLibrary.
- No agent or verifier exceptions appeared in Harbor's job results.

## Interpretation

Harbor integration works end to end. The adapter correctly receives the task
instruction, injects A/B/C conditions, loads the C skill, executes our
`AgentLoop` against Harbor's container, captures patches, and lets the Pro V2
verifier grade them.

The three hard tasks split by task, not by condition: Ansible and qutebrowser
resolved in every condition; OpenLibrary failed in every condition. OpenLibrary
also consumed the 1M-token budget in every condition, and C ended with an empty
patch. This is a task-level floor, not evidence that A, B, or C is better.

**Caveat:** the pilot used the verifier in the same container
(`verifier_environment_mode: shared`). The Pro V2 locked protocol calls for a
fresh-sandbox `patch_replay` re-grade. Main results should use patch replay, not
this shared-verifier path.

## Next

- Freeze a 10-task Python selection across the three Pro V2 Python repos.
- Run 10 tasks x 3 conditions x 1 repeat for the full pilot.
- Use `patch_replay` for authoritative grading.
- Expect some tasks to floor at the 1M-token budget; either keep the cap as part
  of the construct or calibrate it before the main run.
