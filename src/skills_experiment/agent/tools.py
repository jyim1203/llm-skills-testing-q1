"""Agent tools and their executor.

The tool *set* is identical across conditions except for ``load_skill``, which
only Condition C exposes (handoff section 8: a skill runtime may read metadata
or load a file, but must not receive extra coding/execution tools the other
conditions lack).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..sandbox.base import MAX_OUTPUT_CHARS, Sandbox
from ..models.types import ToolCall, ToolSpec


def base_tool_specs() -> list[ToolSpec]:
    """The condition-independent tool set."""
    return [
        ToolSpec(
            name="run_shell",
            description=(
                "Run a shell command in the repository workspace and return its "
                "combined stdout/stderr and exit code."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run."}
                },
                "required": ["command"],
            },
        ),
        ToolSpec(
            name="read_file",
            description=(
                "Read a file from the workspace. Optionally restrict to a line range "
                "(1-based, inclusive). Line numbers are included in the output."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
            },
        ),
        ToolSpec(
            name="write_file",
            description="Create or overwrite a file with the given content.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        ),
        ToolSpec(
            name="list_dir",
            description="List the entries of a directory in the workspace.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": [],
            },
        ),
    ]


def load_skill_tool_spec(skill_names: list[str]) -> ToolSpec:
    """The skill-loading tool, with the available skills enumerated."""
    return ToolSpec(
        name="load_skill",
        description=(
            "Load the full instructions of an available skill by name. Call this "
            "before starting work that the skill describes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the skill to load.",
                    "enum": skill_names,
                }
            },
            "required": ["name"],
        },
    )


@dataclass
class ToolOutcome:
    ok: bool
    content: str
    skill_loaded: bool = False
    error: Optional[str] = None


@dataclass
class ToolExecutor:
    """Dispatches tool calls to a sandbox; tracks skill-loading events."""

    sandbox: Sandbox
    skills_dir: Optional[Path] = None
    tool_timeout_seconds: int = 120
    events: list[dict[str, Any]] = field(default_factory=list)

    def available_skills(self) -> list[str]:
        return sorted(self._skill_index())

    def _skill_index(self) -> dict[str, Path]:
        """Map skill *name* (from front matter) -> SKILL.md path."""
        from ..skills import parse_front_matter

        index: dict[str, Path] = {}
        if not self.skills_dir:
            return index
        root = Path(self.skills_dir)
        if not root.exists():
            return index
        for child in sorted(root.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                meta, _ = parse_front_matter(skill_md.read_text(encoding="utf-8"))
                index[meta.get("name") or child.name] = skill_md
        return index

    def execute(self, call: ToolCall) -> ToolOutcome:
        handler = self._HANDLERS.get(call.name)
        if handler is None:
            outcome = ToolOutcome(ok=False, content="", error=f"unknown tool {call.name!r}")
        else:
            try:
                outcome = handler(self, call.arguments)
            except Exception as exc:  # noqa: BLE001 - surface as a tool error, not a crash
                outcome = ToolOutcome(ok=False, content="", error=f"{type(exc).__name__}: {exc}")
        self.events.append(
            {
                "tool": call.name,
                "arguments": call.arguments,
                "ok": outcome.ok,
                "skill_loaded": outcome.skill_loaded,
                "error": outcome.error,
            }
        )
        body = outcome.content if outcome.ok else f"[error] {outcome.error}"
        return ToolOutcome(ok=outcome.ok, content=body, skill_loaded=outcome.skill_loaded, error=outcome.error)

    # -- handlers ----------------------------------------------------------- #
    def _run_shell(self, args: dict[str, Any]) -> ToolOutcome:
        command = str(args.get("command", "")).strip()
        if not command:
            return ToolOutcome(ok=False, content="", error="empty command")
        result = self.sandbox.run(command, timeout=self.tool_timeout_seconds)
        return ToolOutcome(ok=True, content=result.combined())

    def _read_file(self, args: dict[str, Any]) -> ToolOutcome:
        path = str(args.get("path", ""))
        if not path:
            return ToolOutcome(ok=False, content="", error="missing 'path'")
        text = self.sandbox.read_file(
            path,
            start_line=_as_int(args.get("start_line")),
            end_line=_as_int(args.get("end_line")),
        )
        ok = not text.startswith("[error]")
        # Match the shell-output cap: an uncapped read can blow a small model's
        # context window and silently truncate its system prompt.
        if ok and len(text) > MAX_OUTPUT_CHARS:
            text = (
                text[:MAX_OUTPUT_CHARS]
                + f"\n... [truncated {len(text) - MAX_OUTPUT_CHARS} chars]"
            )
        return ToolOutcome(ok=ok, content=text, error=None if ok else text)

    def _write_file(self, args: dict[str, Any]) -> ToolOutcome:
        path = str(args.get("path", ""))
        if not path:
            return ToolOutcome(ok=False, content="", error="missing 'path'")
        if "content" not in args:
            return ToolOutcome(ok=False, content="", error="missing 'content'")
        text = self.sandbox.write_file(path, str(args["content"]))
        ok = not text.startswith("[error]")
        return ToolOutcome(ok=ok, content=text, error=None if ok else text)

    def _list_dir(self, args: dict[str, Any]) -> ToolOutcome:
        path = str(args.get("path", ".") or ".")
        text = self.sandbox.list_dir(path)
        ok = not text.startswith("[error]")
        return ToolOutcome(ok=ok, content=text, error=None if ok else text)

    def _load_skill(self, args: dict[str, Any]) -> ToolOutcome:
        name = str(args.get("name", "")).strip()
        index = self._skill_index()
        if not index:
            return ToolOutcome(ok=False, content="", error="no skills are available")
        if name not in index:
            return ToolOutcome(
                ok=False,
                content="",
                error=f"unknown skill {name!r}; available: {sorted(index)}",
            )
        text = index[name].read_text(encoding="utf-8")
        return ToolOutcome(
            ok=True,
            content=text,
            skill_loaded=True,
        )


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


ToolExecutor._HANDLERS = {  # type: ignore[attr-defined]
    "run_shell": ToolExecutor._run_shell,
    "read_file": ToolExecutor._read_file,
    "write_file": ToolExecutor._write_file,
    "list_dir": ToolExecutor._list_dir,
    "load_skill": ToolExecutor._load_skill,
}
