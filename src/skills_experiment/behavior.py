"""Extract behavior and efficiency features from Harbor/Pro V2 attempts.

The extractor is deliberately tolerant of two data generations:

* the earlier pilot, which has ``messages.jsonl``/``patch.diff`` but no
  per-call event log;
* the mechanism-study runs, which also have ``events.jsonl`` with timestamps,
  per-call token usage, and tool durations.

It produces one row per attempt plus one row per observed tool event.  The
attempt row is the unit used for task-level paired analysis.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

KNOWN_TOOLS = {"run_shell", "read_file", "write_file", "list_dir", "load_skill"}

TEST_RE = re.compile(
    r"(?:^|[\s;&|])(?:pytest|py\.test|tox|nox|ansible-test|python(?:3)?\s+-m\s+"
    r"(?:pytest|unittest)|unittest|npm\s+test|yarn\s+test|cargo\s+test|go\s+test)"
    r"(?:\s|$)",
    re.IGNORECASE,
)
SEARCH_RE = re.compile(r"\b(?:grep|rg|ripgrep|find|git\s+grep|ack|ag)\b", re.IGNORECASE)
READ_SHELL_RE = re.compile(r"\b(?:cat|head|tail|sed\s+-n|less|more|wc)\b", re.IGNORECASE)
EDIT_SHELL_RE = re.compile(
    r"(?:sed\s+-i|perl\s+-pi|tee\s+|git\s+apply|patch\s+-p|"
    r">\s*[^&\s]+|>>\s*[^&\s]+|\bpython[0-9.]*\s+-c\b.*\bopen\()",
    re.IGNORECASE,
)
GIT_RE = re.compile(r"\bgit\b", re.IGNORECASE)
INSTALL_RE = re.compile(r"\b(?:pip|pip3|uv|poetry|pipenv|conda|npm|yarn|apt-get)\b", re.IGNORECASE)

DIFF_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)
DIFF_ADD_RE = re.compile(r"^\+(?!\+\+)", re.MULTILINE)
DIFF_DEL_RE = re.compile(r"^-(?!--)", re.MULTILINE)


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _json_list(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(item) for item in value if str(item).strip()}
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {value.strip()}
        if isinstance(parsed, list):
            return {str(item) for item in parsed if str(item).strip()}
    return set()


def load_dataset_index(path: Optional[Path]) -> dict[str, dict[str, Any]]:
    """Map instance_id -> row, with fail/pass sets parsed."""
    if path is None or not Path(path).exists():
        return {}
    rows = _load_json(Path(path), [])
    if not isinstance(rows, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        instance_id = str(row.get("instance_id") or "")
        if not instance_id:
            continue
        item = dict(row)
        item["_fail_to_pass"] = _json_list(row.get("fail_to_pass"))
        item["_pass_to_pass"] = _json_list(row.get("pass_to_pass"))
        index[instance_id] = item
    return index


def iter_job_dirs(root: Path) -> list[Path]:
    root = Path(root)
    if (root / "result.json").exists() and (root / "config.json").exists():
        return [root]
    if not root.exists():
        return []
    return sorted(
        child for child in root.iterdir() if child.is_dir() and (child / "result.json").exists()
    )


def _trial_dirs(job_dir: Path) -> list[Path]:
    return sorted(
        child
        for child in job_dir.iterdir()
        if child.is_dir() and (child / "result.json").exists()
    )


def _condition(trial: dict[str, Any], config: dict[str, Any]) -> str:
    metadata = (trial.get("agent_result") or {}).get("metadata") or {}
    raw = str(metadata.get("condition") or "")
    if not raw:
        raw = str(((config.get("agent") or {}).get("kwargs") or {}).get("condition") or "")
    low = raw.lower()
    if low.startswith("a") or low == "baseline":
        return "A"
    if low.startswith("b"):
        return "B"
    if low.startswith("c"):
        return "C"
    return raw or "?"


def _task_id(trial: dict[str, Any], config: dict[str, Any]) -> str:
    task_name = str(trial.get("task_name") or "")
    if task_name.startswith("swebench-pro/"):
        return task_name[len("swebench-pro/") :]
    task_path = str(((config.get("task") or {}).get("path") or ""))
    if task_path:
        return Path(task_path).name
    return task_name


def _repeat(trial: dict[str, Any], config: dict[str, Any]) -> Optional[int]:
    metadata = (trial.get("agent_result") or {}).get("metadata") or {}
    for source in (metadata, (config.get("agent") or {}).get("kwargs") or {}):
        value = source.get("repeat")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _message_events(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recover tool-call order and results from a transcript."""
    results: dict[str, dict[str, Any]] = {}
    for msg in messages:
        if msg.get("role") == "tool":
            call_id = str(msg.get("tool_call_id") or "")
            if call_id:
                results[call_id] = msg

    events: list[dict[str, Any]] = []
    model_call = 0
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        model_call += 1
        for call in msg.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            call_id = str(call.get("id") or "")
            result = results.get(call_id, {})
            content = str(result.get("content") or "")
            events.append(
                {
                    "event": "tool_call",
                    "source": "messages",
                    "model_call": model_call,
                    "tool": str(call.get("name") or ""),
                    "arguments": call.get("arguments") or {},
                    "result": content,
                    "result_chars": len(content),
                    "result_error": content.startswith("[error]"),
                    "exit_code": None,
                    "duration_ms": None,
                    "step": model_call,
                }
            )
    return events


def _events_from_file(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for event in events:
        if event.get("event") != "tool_call":
            continue
        out.append(
            {
                "event": "tool_call",
                "source": "events_jsonl",
                "model_call": event.get("step"),
                "tool": event.get("tool") or "",
                "arguments": event.get("arguments") or {},
                "result": "",
                "result_chars": event.get("output_chars"),
                "result_error": event.get("ok") is False,
                "exit_code": event.get("exit_code"),
                "duration_ms": event.get("duration_ms"),
                "step": event.get("step"),
                "timestamp": event.get("timestamp"),
                "result_sha256": event.get("result_sha256"),
                "error": event.get("error"),
            }
        )
    return out


def _effective_events(messages: list[dict[str, Any]], raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from_events = _events_from_file(raw_events)
    return from_events or _message_events(messages)


def _classify(tool: str, args: dict[str, Any]) -> dict[str, bool]:
    command = str(args.get("command") or "")
    if tool == "write_file":
        return {
            "is_edit": True,
            "is_test": False,
            "is_read": False,
            "is_search": False,
            "is_git": False,
            "is_install": False,
        }
    if tool == "read_file":
        return {
            "is_edit": False,
            "is_test": False,
            "is_read": True,
            "is_search": False,
            "is_git": False,
            "is_install": False,
        }
    if tool == "list_dir":
        return {
            "is_edit": False,
            "is_test": False,
            "is_read": True,
            "is_search": True,
            "is_git": False,
            "is_install": False,
        }
    if tool == "load_skill":
        return {
            "is_edit": False,
            "is_test": False,
            "is_read": False,
            "is_search": False,
            "is_git": False,
            "is_install": False,
        }
    if tool == "run_shell":
        is_test = bool(TEST_RE.search(command))
        is_search = bool(SEARCH_RE.search(command))
        is_edit = bool(EDIT_SHELL_RE.search(command)) and not is_test
        is_read = bool(READ_SHELL_RE.search(command)) and not is_edit and not is_test
        return {
            "is_edit": is_edit,
            "is_test": is_test,
            "is_read": is_read,
            "is_search": is_search,
            "is_git": bool(GIT_RE.search(command)),
            "is_install": bool(INSTALL_RE.search(command)),
        }
    return {
        "is_edit": False,
        "is_test": False,
        "is_read": False,
        "is_search": False,
        "is_git": False,
        "is_install": False,
    }


def _command_paths(command: str) -> list[str]:
    """Best-effort file paths from a shell command."""
    return re.findall(
        r"[A-Za-z0-9_./-]+\.(?:py|pyi|toml|cfg|ini|yml|yaml|json|md|txt)",
        command,
    )


def _patch_stats(patch: str) -> dict[str, Any]:
    files = sorted({m.group(2) for m in DIFF_FILE_RE.finditer(patch)})
    added = len(DIFF_ADD_RE.findall(patch))
    removed = len(DIFF_DEL_RE.findall(patch))
    return {
        "patch_chars": len(patch),
        "patch_files": len(files),
        "patch_file_names": files,
        "patch_lines_added": added,
        "patch_lines_removed": removed,
        "patch_lines_changed": added + removed,
    }


def _message_features(messages: list[dict[str, Any]]) -> dict[str, Any]:
    system_chars = 0
    user_chars = 0
    assistant_messages = 0
    reasoning_chars = 0
    tool_calls = 0
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            system_chars += len(str(msg.get("content") or ""))
        elif role == "user":
            user_chars += len(str(msg.get("content") or ""))
        elif role == "assistant":
            assistant_messages += 1
            reasoning_chars += len(str(msg.get("reasoning_content") or ""))
            tool_calls += len(msg.get("tool_calls") or [])
    return {
        "system_prompt_chars": system_chars,
        "task_prompt_chars": user_chars,
        "assistant_messages": assistant_messages,
        "reasoning_chars": reasoning_chars,
        "tool_call_messages": tool_calls,
    }


def _parse_timestamp(value: Any):
    if not value:
        return None
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_metrics(raw_events: list[dict[str, Any]]) -> dict[str, Any]:
    model_calls = [e for e in raw_events if e.get("event") == "model_call"]
    tool_events = [e for e in raw_events if e.get("event") == "tool_call"]
    prompt_tokens = 0
    completion_tokens = 0
    cache_read_tokens = 0
    reasoning_tokens = 0
    reasoning_chars = 0
    model_latency_ms = 0.0
    for event in model_calls:
        usage = event.get("usage") or {}
        prompt_tokens += int(usage.get("input_tokens") or 0)
        completion_tokens += int(usage.get("output_tokens") or 0)
        cache_read_tokens += int(usage.get("cache_read_tokens") or 0)
        reasoning_tokens += int(usage.get("reasoning_tokens") or 0)
        reasoning_chars += int(event.get("reasoning_chars") or 0)
        model_latency_ms += float(event.get("latency_ms") or 0)
    tool_duration_ms = sum(float(e.get("duration_ms") or 0) for e in tool_events)

    start_event = next((e for e in raw_events if e.get("event") == "run_start"), None)
    start_ts = _parse_timestamp((start_event or {}).get("timestamp"))
    first_edit_ts = None
    first_test_ts = None
    for event in tool_events:
        args = event.get("arguments") or {}
        if not isinstance(args, dict):
            args = {}
        flags = _classify(str(event.get("tool") or ""), args)
        ts = _parse_timestamp(event.get("timestamp"))
        if ts is None:
            continue
        if flags["is_edit"] and first_edit_ts is None:
            first_edit_ts = ts
        if flags["is_test"] and first_test_ts is None:
            first_test_ts = ts
    time_to_first_edit = (
        (first_edit_ts - start_ts).total_seconds() if start_ts and first_edit_ts else None
    )
    time_to_first_test = (
        (first_test_ts - start_ts).total_seconds() if start_ts and first_test_ts else None
    )
    return {
        "events_model_calls": len(model_calls),
        "events_tool_calls": len(tool_events),
        "events_prompt_tokens": prompt_tokens,
        "events_completion_tokens": completion_tokens,
        "events_cache_read_tokens": cache_read_tokens,
        "events_reasoning_tokens": reasoning_tokens,
        "events_reasoning_chars": reasoning_chars,
        "model_latency_ms": round(model_latency_ms, 3),
        "tool_duration_ms": round(tool_duration_ms, 3),
        "time_to_first_edit_seconds": time_to_first_edit,
        "time_to_first_test_seconds": time_to_first_test,
    }


def _verifier_features(
    trial_dir: Path,
    dataset_row: Optional[dict[str, Any]],
    reward: Optional[float],
) -> dict[str, Any]:
    output = _load_json(trial_dir / "verifier" / "output.json", {}) or {}
    tests = output.get("tests") or []
    statuses: dict[str, str] = {}
    for test in tests:
        if isinstance(test, dict):
            name = str(test.get("name") or "")
            status = str(test.get("status") or "")
            if name:
                statuses[name] = status.upper()
    f2p = set(dataset_row.get("_fail_to_pass") or []) if dataset_row else set()
    p2p = set(dataset_row.get("_pass_to_pass") or []) if dataset_row else set()
    f2p_passed = sum(1 for name in f2p if statuses.get(name) in {"PASSED", "PASS", "OK"})
    p2p_passed = sum(1 for name in p2p if statuses.get(name) in {"PASSED", "PASS", "OK"})
    passed_total = sum(1 for status in statuses.values() if status in {"PASSED", "PASS", "OK"})
    failed_total = sum(1 for status in statuses.values() if status in {"FAILED", "FAIL", "ERROR"})
    resolved = bool(reward is not None and reward >= 1.0)
    return {
        "resolved": resolved,
        "reward": reward,
        "f2p_total": len(f2p),
        "f2p_passed": f2p_passed,
        "f2p_fraction": (f2p_passed / len(f2p)) if f2p else None,
        "p2p_total": len(p2p),
        "p2p_passed": p2p_passed,
        "p2p_fraction": (p2p_passed / len(p2p)) if p2p else None,
        "tests_total": len(statuses),
        "tests_passed": passed_total,
        "tests_failed": failed_total,
        "tests_status": statuses,
    }


def _behavior_features(events: list[dict[str, Any]], metadata: dict[str, Any], patch: str) -> dict[str, Any]:
    counts = {
        "tool_calls": 0,
        "run_shell_calls": 0,
        "read_file_calls": 0,
        "write_file_calls": 0,
        "list_dir_calls": 0,
        "load_skill_calls": 0,
        "test_calls": 0,
        "edit_calls": 0,
        "read_calls": 0,
        "search_calls": 0,
        "git_calls": 0,
        "install_calls": 0,
        "tool_errors": 0,
        "unknown_tool_calls": 0,
    }
    edit_indices: list[int] = []
    test_indices: list[int] = []
    read_indices: list[int] = []
    commands: list[str] = []
    files_read: set[str] = set()
    files_edited: set[str] = set()
    skill_loads = 0
    first_skill_step: Optional[int] = None

    for index, event in enumerate(events):
        tool = str(event.get("tool") or "")
        args = event.get("arguments") or {}
        if not isinstance(args, dict):
            args = {}
        flags = _classify(tool, args)
        counts["tool_calls"] += 1
        counts[f"{tool}_calls"] = counts.get(f"{tool}_calls", 0) + 1
        counts["test_calls"] += int(flags["is_test"])
        counts["edit_calls"] += int(flags["is_edit"])
        counts["read_calls"] += int(flags["is_read"])
        counts["search_calls"] += int(flags["is_search"])
        counts["git_calls"] += int(flags["is_git"])
        counts["install_calls"] += int(flags["is_install"])
        if flags["is_edit"]:
            edit_indices.append(index)
        if flags["is_test"]:
            test_indices.append(index)
        if flags["is_read"] or flags["is_search"]:
            read_indices.append(index)
        command = str(args.get("command") or "")
        if command:
            commands.append(_normalize_command(command))
        path = str(args.get("path") or "")
        if path:
            if tool == "read_file":
                files_read.add(path)
            elif tool == "write_file":
                files_edited.add(path)
        else:
            for candidate in _command_paths(command):
                if flags["is_read"]:
                    files_read.add(candidate)
                if flags["is_edit"]:
                    files_edited.add(candidate)
        if event.get("result_error") or event.get("error"):
            counts["tool_errors"] += 1
        if tool not in KNOWN_TOOLS:
            counts["unknown_tool_calls"] += 1
        if tool == "load_skill" and not event.get("result_error"):
            skill_loads += 1
            if first_skill_step is None:
                first_skill_step = index

    first_edit = edit_indices[0] if edit_indices else None
    last_edit = edit_indices[-1] if edit_indices else None
    repeated = len(commands) - len(set(commands))
    patch_stats = _patch_stats(patch)
    stop_reason = str(metadata.get("stop_reason") or "")
    return {
        **counts,
        "first_edit_event": first_edit,
        "last_edit_event": last_edit,
        "test_before_edit": bool(first_edit is not None and any(i < first_edit for i in test_indices)),
        "read_before_edit": bool(first_edit is not None and any(i < first_edit for i in read_indices)),
        "test_after_last_edit": bool(last_edit is not None and any(i > last_edit for i in test_indices)),
        "verification_rate": int(bool(last_edit is not None and any(i > last_edit for i in test_indices))),
        "unique_files_read": len(files_read),
        "unique_files_edited": len(files_edited),
        "skill_loads": skill_loads,
        "first_skill_event": first_skill_step,
        "repeated_commands": repeated,
        "stop_reason": stop_reason,
        "budget_exhausted": stop_reason in {"token_budget", "elapsed_budget"},
        "skill_loaded": bool(metadata.get("skill_loaded") or skill_loads),
        **patch_stats,
    }


def _normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


def extract_attempt(
    trial_dir: Path,
    job_dir: Path,
    dataset_index: Optional[dict[str, dict[str, Any]]] = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trial_dir = Path(trial_dir)
    job_dir = Path(job_dir)
    trial = _load_json(trial_dir / "result.json", {}) or {}
    config = _load_json(trial_dir / "config.json", {}) or {}
    agent_result = trial.get("agent_result") or {}
    metadata = agent_result.get("metadata") or {}
    reward = (trial.get("verifier_result") or {}).get("rewards", {}).get("reward")
    try:
        reward = float(reward) if reward is not None else None
    except (TypeError, ValueError):
        reward = None

    messages = _load_jsonl(trial_dir / "agent" / "messages.jsonl")
    raw_events = _load_jsonl(trial_dir / "agent" / "events.jsonl")
    patch_path = trial_dir / "agent" / "patch.diff"
    patch = patch_path.read_text(encoding="utf-8", errors="replace") if patch_path.exists() else ""
    task_id = _task_id(trial, config)
    dataset_row = (dataset_index or {}).get(task_id)

    events = _effective_events(messages, raw_events)
    message_features = _message_features(messages)
    behavior = _behavior_features(events, metadata, patch)
    event_metrics = _event_metrics(raw_events)
    verifier = _verifier_features(trial_dir, dataset_row, reward)
    started_at = trial.get("started_at")
    finished_at = trial.get("finished_at")
    wall_seconds = None
    if started_at and finished_at:
        try:
            from datetime import datetime

            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(finished_at).replace("Z", "+00:00"))
            wall_seconds = (end - start).total_seconds()
        except ValueError:
            wall_seconds = None

    attempt = {
        "schema_version": "1",
        "attempt_id": f"{job_dir.name}/{trial_dir.name}",
        "job_id": str(trial.get("config", {}).get("job_id") or job_dir.name),
        "job_dir": str(job_dir),
        "trial_name": trial_dir.name,
        "task_id": task_id,
        "task_name": trial.get("task_name") or "",
        "condition": _condition(trial, config),
        "repeat": _repeat(trial, config),
        "model_id": ((trial.get("agent_info") or {}).get("model_info") or {}).get("name")
        if isinstance((trial.get("agent_info") or {}).get("model_info"), dict)
        else None,
        "started_at": started_at,
        "finished_at": finished_at,
        "wall_seconds": wall_seconds,
        "verifier_environment_mode": trial.get("verifier_environment_mode"),
        "exception": bool(trial.get("exception_info")),
        "exception_info": trial.get("exception_info"),
        "input_tokens": int(agent_result.get("n_input_tokens") or 0),
        "output_tokens": int(agent_result.get("n_output_tokens") or 0),
        "reasoning_tokens": metadata.get("reasoning_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "total_tokens": int(agent_result.get("n_input_tokens") or 0)
        + int(agent_result.get("n_output_tokens") or 0),
        "steps": metadata.get("steps"),
        "tool_call_count_metadata": metadata.get("tool_call_count"),
        "stop_reason_metadata": metadata.get("stop_reason"),
        "skill_loaded_metadata": metadata.get("skill_loaded"),
        "errors_metadata": metadata.get("errors"),
        "workflow_version": metadata.get("workflow_version"),
        "workflow_sha256": metadata.get("workflow_sha256"),
        "system_prompt_sha256": metadata.get("system_prompt_sha256"),
        "task_prompt_sha256": metadata.get("task_prompt_sha256"),
        **message_features,
        **behavior,
        **event_metrics,
        **verifier,
    }
    event_rows: list[dict[str, Any]] = []
    for event in events:
        event_rows.append(
            {
                "attempt_id": attempt["attempt_id"],
                "job_id": attempt["job_id"],
                "trial_name": attempt["trial_name"],
                "task_id": attempt["task_id"],
                "condition": attempt["condition"],
                "repeat": attempt["repeat"],
                "event": event.get("event"),
                "source": event.get("source"),
                "step": event.get("step"),
                "model_call": event.get("model_call"),
                "tool": event.get("tool"),
                "arguments": json.dumps(event.get("arguments") or {}, ensure_ascii=False),
                "result_chars": event.get("result_chars"),
                "result_error": event.get("result_error"),
                "exit_code": event.get("exit_code"),
                "duration_ms": event.get("duration_ms"),
            }
        )
    return attempt, event_rows


def extract(root: Path, dataset: Optional[Path] = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dataset_index = load_dataset_index(dataset)
    attempts: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for job_dir in iter_job_dirs(Path(root)):
        for trial_dir in _trial_dirs(job_dir):
            attempt, attempt_events = extract_attempt(trial_dir, job_dir, dataset_index)
            attempts.append(attempt)
            events.extend(attempt_events)
    return attempts, events


def write_attempts_csv(path: Path, attempts: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not attempts:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    seen: set[str] = set()
    for row in attempts:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    import csv

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in attempts:
            writer.writerow({key: _csv_value(row.get(key)) for key in columns})


def write_events_csv(path: Path, events: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "attempt_id",
        "job_id",
        "trial_name",
        "task_id",
        "condition",
        "repeat",
        "event",
        "source",
        "step",
        "model_call",
        "tool",
        "arguments",
        "result_chars",
        "result_error",
        "exit_code",
        "duration_ms",
    ]
    import csv

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in events:
            writer.writerow({key: _csv_value(row.get(key)) for key in columns})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict, set, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value
