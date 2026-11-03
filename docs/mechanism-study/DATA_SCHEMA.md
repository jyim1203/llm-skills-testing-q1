# Data Schema

This schema is the contract between the Harbor agent, the behavior extractor, and
the analysis. Raw events are append-only; derived tables are regenerated.

## Directory layout

```text
jobs/<job>/
  result.json                 Harbor job summary
  <trial>/
    result.json               per-trial result and agent metadata
    config.json               task/agent/condition/repeat
    agent/
      messages.jsonl          full normalized transcript
      events.jsonl            structured event stream (new runs)
      patch.diff              captured patch
    verifier/
      output.json             test names + statuses
      reward.txt              verifier reward

data/derived/
  attempts.csv                one row per attempt
  events.csv                  one row per tool event
  attempts.json               inspectable copy
```

## Provenance fields

| Field | Type | Notes |
|---|---|---|
| `attempt_id` | string | `<job>/<trial>` |
| `job_id` | string | Harbor job UUID |
| `trial_name` | string | Harbor trial directory |
| `task_id` | string | Pro V2 instance ID |
| `task_name` | string | Harbor task name |
| `condition` | `A` / `B` / `C` | Normalized from metadata |
| `repeat` | int/null | Repeat index |
| `model_id` | string/null | Provider model ID |
| `workflow_version` | string | `v3` for this study |
| `workflow_sha256` | string | V3 body hash |
| `system_prompt_sha256` | string | Exact system prompt hash |
| `task_prompt_sha256` | string | Exact task prompt hash |
| `started_at`, `finished_at` | ISO 8601 | UTC |
| `wall_seconds` | float/null | Trial wall time |
| `verifier_environment_mode` | string/null | `shared` / `patch_replay` |
| `exception` | bool | Harbor exception present |
| `exception_info` | object/null | Raw exception metadata |

## Event stream (`agent/events.jsonl`)

Every row has:

| Field | Type | Notes |
|---|---|---|
| `event` | string | `run_start`, `model_call`, `tool_call`, `run_end` |
| `timestamp` | ISO 8601 | UTC |
| `time_unix` | float | Wall clock |
| `attempt_id` | string | Base field |
| `trial_name` | string | Base field |
| `job_dir` | string | Base field |
| `run_id` | string | Optional external run ID |
| `task_id` | string | Optional; set by launcher |
| `repeat` | int/null | Base field |
| `condition` | string | `A_baseline`, `B_prompt_instructions`, `C_skill` |
| `model_id` | string | Base field |
| `workflow_version` | string | Base field |
| `workflow_sha256` | string | Base field |
| `system_prompt_sha256` | string | Base field |
| `task_prompt_sha256` | string | Base field |
| `repo_root` | string | Container repo root |
| `base_ref` | string | Git base commit |
| `max_steps` | int | Budget |
| `max_tokens` | int | Budget |
| `elapsed_seconds` | int | Budget |

### `run_start`

Extra fields:

- `system_prompt_chars`
- `task_prompt_chars`
- `tool_names` (list)
- `max_steps`, `max_tokens`, `elapsed_seconds`

### `model_call`

Extra fields:

| Field | Type | Notes |
|---|---|---|
| `step` | int | Agent loop step |
| `latency_ms` | float | Wall time for the API call |
| `model_id` | string | Response model |
| `finish_reason` | string/null | Provider finish reason |
| `tool_call_count` | int | Tool calls requested |
| `tool_names` | list | Tool names requested |
| `text_chars` | int | Assistant text length |
| `reasoning_chars` | int | Thinking length |
| `messages_count` | int | Context size before the call |
| `usage` | object | `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens` |

Reasoning text itself is in `messages.jsonl` (`reasoning_content`); the event
stores its length to keep the event log small.

### `tool_call`

Extra fields:

| Field | Type | Notes |
|---|---|---|
| `step` | int | Agent loop step |
| `tool` | string | Tool name |
| `arguments` | object | Sanitized; `write_file.content` is replaced by length/hash |
| `ok` | bool | Handler success |
| `skill_loaded` | bool | True for a successful `load_skill` |
| `error` | string/null | Handler error |
| `exit_code` | int/null | Shell exit code |
| `duration_ms` | float | Tool duration |
| `output_chars` | int | Result length |
| `result_sha256` | string | Result hash |

Full tool output is in `messages.jsonl`; `result_sha256` links the event to it.

### `run_end`

Extra fields:

- `steps`
- `stop_reason`
- `tool_call_count`
- `patch_chars`
- `skill_discovered`
- `skill_loaded`
- `errors` (list)
- `usage` (aggregate)
- `elapsed_seconds`

## Attempt-level derived fields

### Tokens and time

| Field | Type | Notes |
|---|---|---|
| `input_tokens`, `output_tokens` | int | From provider result |
| `total_tokens` | int | Input + output |
| `cache_tokens` | int/null | Provider cache field |
| `model_latency_ms` | float | Sum of model calls (events only) |
| `tool_duration_ms` | float | Sum of tool calls (events only) |
| `time_to_first_edit_seconds` | float/null | From `run_start` |
| `time_to_first_test_seconds` | float/null | From `run_start` |
| `wall_seconds` | float/null | Trial wall time |

### Behavior

| Field | Type | Notes |
|---|---|---|
| `tool_calls` | int | Total tool calls |
| `run_shell_calls`, `read_file_calls`, `write_file_calls`, `list_dir_calls`, `load_skill_calls` | int | Tool mix |
| `test_calls` | int | Detected test invocations |
| `edit_calls` | int | `write_file` or shell edit |
| `read_calls`, `search_calls` | int | Inspection actions |
| `git_calls`, `install_calls` | int | Shell categories |
| `first_edit_event`, `last_edit_event` | int/null | Event indexes |
| `read_before_edit` | bool | Read/search/list before first edit |
| `test_before_edit` | bool | Test before first edit |
| `test_after_last_edit` | bool | Test after last edit |
| `verification_rate` | 0/1 | Same as `test_after_last_edit` when an edit exists |
| `unique_files_read`, `unique_files_edited` | int | Best-effort |
| `skill_loads`, `first_skill_event` | int/null | Treatment check |
| `repeated_commands` | int | Duplicate normalized shell commands |
| `tool_errors` | int | Error results |
| `unknown_tool_calls` | int | Tool name outside the shared set |
| `stop_reason` | string | `stop`, `token_budget`, etc. |
| `budget_exhausted` | bool | `token_budget` or `elapsed_budget` |

### Patch

| Field | Type |
|---|---|
| `patch_chars` | int |
| `patch_files` | int |
| `patch_file_names` | list[str] |
| `patch_lines_added` | int |
| `patch_lines_removed` | int |
| `patch_lines_changed` | int |

### Outcome

| Field | Type | Notes |
|---|---|---|
| `resolved` | bool | Reward >= 1.0 |
| `reward` | float/null | Verifier reward |
| `f2p_total`, `f2p_passed` | int | From dataset membership + verifier statuses |
| `f2p_fraction` | float/null | Partial-credit outcome |
| `p2p_total`, `p2p_passed` | int | Pass-to-pass |
| `p2p_fraction` | float/null | |
| `tests_total`, `tests_passed`, `tests_failed` | int | Verifier output |
| `tests_status` | object | Name -> status |

## Rules

- Raw `messages.jsonl`, `events.jsonl`, `patch.diff`, and verifier output are
  immutable after an attempt.
- Derived tables include a schema version when written by analysis scripts.
- Missing event data is `null`, not zero.
- `reasoning_content` is stored in the transcript; never synthesize it.
- API keys and authorization headers must never enter any log.
