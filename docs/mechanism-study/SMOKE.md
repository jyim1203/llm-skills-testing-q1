# v2 Smoke Validation

**Status:** passed  
**Task:** `instance_ansible__ansible-e9e600...` (known ceiling)  
**Workflow:** v2  
**Attempts:** A, B, C once each  
**Included in the 60:** no

| Condition | Resolved | Steps | Tool calls | Input tokens | Output tokens | Skill loaded |
|---|---:|---:|---:|---:|---:|---|
| A baseline | yes | 13 | 15 | 241,095 | 8,713 | no |
| B prompt | yes | 14 | 17 | 265,343 | 12,137 | no |
| C skill | yes | 28 | 31 | 668,260 | 11,601 | yes |

All three:

- resolved with F2P 8/8 and P2P 20/20
- wrote `events.jsonl` with `run_start`, `model_call`, `tool_call`, `run_end`
- had monotonic UTC timestamps
- had non-zero per-call input/output tokens
- had reasoning tokens and `reasoning_chars`
- had tool durations and shell exit codes
- produced `messages.jsonl`, `patch.diff`, verifier output, and an extractor row

Condition wiring:

- A system prompt: 228 chars
- B system prompt: 2,106 chars
- C system prompt: 711 chars
- C loaded `python-repo-maintenance` at the first tool call
- A/B made zero `load_skill` calls

Notable behavior: C resolved but its last edit came after its last test, so
`verification_rate = 0` in the extractor. That is a valid behavioral observation,
not a smoke failure.

The smoke is excluded from the 60-attempt mechanism analysis.
