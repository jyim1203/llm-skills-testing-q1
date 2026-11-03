"""Harbor adapter for the skills experiment.

This is intentionally a *thin* boundary:

* Harbor owns the task container, network policy, timeout, and verifier.
* ``AgentLoop``, the model client, and the A/B/C condition text are unchanged.
* ``HarborSandbox`` bridges the synchronous tool executor to Harbor's async
  ``environment.exec`` API.

Run with::

    PYTHONPATH=src harbor run -p /path/to/Pro/v2/tasks \
      -i <instance_id> \
      --agent skills_experiment.harbor_agent:HarborSkillsAgent \
      --ak condition=A \
      --ak task_id=<instance_id> \
      --ak repeat=0 \
      -n 1 -y
"""

from __future__ import annotations

import asyncio
import base64
import json
import shlex
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from harbor.agents.base import BaseAgent
from harbor.agents.capabilities import AgentCapabilities
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from .agent.loop import AgentLoop
from .agent.tools import ToolExecutor, base_tool_specs, load_skill_tool_spec
from .conditions.base import SessionSpec
from .models.registry import get_registry
from .observability import EventRecorder, sha256_text
from .sandbox.base import CommandResult, Sandbox
from .skills import build_skill_doc, write_skill_md
from . import paths


def _quote(value: str) -> str:
    return shlex.quote(value)


class HarborSandbox(Sandbox):
    """Synchronous tool interface over a Harbor environment.

    ``AgentLoop`` is synchronous, while Harbor's environment API is async. The
    agent runs the loop in ``asyncio.to_thread``; this class schedules each
    environment call back on the main event loop and waits for it.
    """

    def __init__(
        self,
        environment: BaseEnvironment,
        loop: asyncio.AbstractEventLoop,
        workdir: Path,
        repo_root: str,
        base_ref: str,
        *,
        default_timeout: int = 120,
    ) -> None:
        super().__init__(workdir)
        self.environment = environment
        self.loop = loop
        self.repo_root = repo_root.rstrip("/") or "/"
        self.base_ref = base_ref or "HEAD"
        self.default_timeout = default_timeout

    def _container_path(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return f"{self.repo_root}/{path}" if path not in ("", ".") else self.repo_root

    def _exec(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        timeout = int(timeout or self.default_timeout)
        future = asyncio.run_coroutine_threadsafe(
            self.environment.exec(
                command=command,
                cwd=self.repo_root,
                timeout_sec=timeout,
            ),
            self.loop,
        )
        try:
            result = future.result(timeout=timeout + 30)
        except TimeoutError:
            future.cancel()
            return CommandResult(command=command, exit_code=124, timed_out=True)
        return CommandResult(
            command=command,
            exit_code=int(result.return_code),
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    def prepare(self, task: Any) -> None:
        return None

    def cleanup(self) -> None:
        return None

    def run(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        return self._exec(command, timeout=timeout)

    def read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        cpath = self._container_path(path)
        result = self._exec(f"cat {_quote(cpath)}")
        if result.exit_code != 0:
            return f"[error] could not read {path}: {result.stderr.strip()}"
        lines = result.stdout.splitlines()
        lo = start_line or 1
        hi = end_line or len(lines)
        width = len(str(hi))
        return "\n".join(
            f"{i + lo:>{width}}: {line}"
            for i, line in enumerate(lines[lo - 1 : hi])
        )

    def write_file(self, path: str, content: str) -> str:
        cpath = self._container_path(path)
        payload = base64.b64encode(content.encode("utf-8")).decode("ascii")
        command = (
            f"mkdir -p \"$(dirname {_quote(cpath)})\" && "
            f"printf %s {_quote(payload)} | base64 -d > {_quote(cpath)}"
        )
        result = self._exec(command)
        if result.exit_code != 0:
            return f"[error] could not write {path}: {result.stderr.strip()}"
        return f"[ok] wrote {len(content)} bytes to {path}"

    def list_dir(self, path: str = ".") -> str:
        cpath = self._container_path(path)
        result = self._exec(f"ls -1 {_quote(cpath)}")
        if result.exit_code != 0:
            return f"[error] could not list {path}: {result.stderr.strip()}"
        return result.stdout.strip() or "(empty)"

    def diff(self) -> str:
        result = self._exec(
            f"git add -A && git diff --cached --no-color {_quote(self.base_ref)}",
            timeout=120,
        )
        return result.stdout


class HarborSkillsAgent(BaseAgent):
    """Run our A/B/C agent inside a Harbor task environment."""

    capabilities = AgentCapabilities(windows=False)
    DEFAULT_SETUP_TIMEOUT_SEC = 300.0

    def __init__(
        self,
        logs_dir: Path,
        task_dir: Path | None = None,
        trial_paths: Any = None,
        model_name: str | None = None,
        condition: str = "A",
        workflow_version: str = "v2",
        task_id: str = "",
        repeat: int | None = None,
        run_id: str = "",
        max_steps: int = 80,
        max_tokens: int = 1_000_000,
        elapsed_seconds: int = 3000,
        tool_timeout_seconds: int = 120,
        agent_timeout_sec: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            logs_dir=logs_dir,
            model_name=model_name,
            **kwargs,
        )
        self.task_dir = Path(task_dir) if task_dir is not None else None
        self.trial_paths = trial_paths
        self.condition = condition
        self.workflow_version = workflow_version
        self.task_id = task_id
        self.repeat = repeat
        self.run_id = run_id
        self.max_steps = int(max_steps)
        self.max_tokens = int(max_tokens)
        self.elapsed_seconds = int(elapsed_seconds)
        self.tool_timeout_seconds = int(tool_timeout_seconds)
        self.repo_root = ""
        self.base_ref = "HEAD"

    @staticmethod
    def name() -> str:
        return "skills-experiment"

    def version(self) -> str:
        return "0.2.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        # Discover the repository root once. Pro V2 uses /app for most tasks
        # and /testbed for a few; do not hard-code either.
        result = await environment.exec(
            "if [ -d /app/.git ]; then echo /app; "
            "elif [ -d /testbed/.git ]; then echo /testbed; "
            "else pwd; fi",
        )
        self.repo_root = (result.stdout or "").strip().splitlines()[-1] or "/app"
        base = await environment.exec(
            f"git -C {_quote(self.repo_root)} rev-parse HEAD",
        )
        self.base_ref = (base.stdout or "").strip() or "HEAD"

    def _condition_spec(self, instruction: str) -> tuple[SessionSpec, Optional[Path]]:
        base_prompt = (
            paths.PROMPTS_DIR / "base_system_prompt_minimal.md"
        ).read_text(encoding="utf-8").strip()
        workflow_file = f"workflow_instructions_{self.workflow_version}.md"
        workflow = (
            paths.PROMPTS_DIR / workflow_file
        ).read_text(encoding="utf-8").strip()
        common = {
            "workflow_version": self.workflow_version,
            "workflow_file": workflow_file,
            "workflow_sha256": sha256_text(workflow),
        }

        name = self.condition.strip()
        if name in ("A", "A_baseline", "baseline"):
            return (
                SessionSpec(
                    condition_name="A_baseline",
                    system_prompt=base_prompt,
                    tools=base_tool_specs(),
                    task_prompt=instruction,
                    metadata={**common, "condition": "A_baseline"},
                ),
                None,
            )

        if name in ("B", "B_prompt_instructions", "prompt_instructions"):
            return (
                SessionSpec(
                    condition_name="B_prompt_instructions",
                    system_prompt=(
                        f"{base_prompt}\n\n# Workflow instructions\n\n{workflow}"
                    ),
                    tools=base_tool_specs(),
                    task_prompt=instruction,
                    metadata={**common, "condition": "B_prompt_instructions"},
                ),
                None,
            )

        if name not in ("C", "C_skill", "skill"):
            raise ValueError(
                f"Unknown condition {self.condition!r}; expected A, B, or C"
            )

        skill = build_skill_doc(
            workflow,
            source=f"assets/prompts/{workflow_file}",
        )
        # ToolExecutor expects the *parent* skills directory and discovers
        # child directories containing SKILL.md.
        skills_root = Path(self.logs_dir) / "skills"
        write_skill_md(skill, skills_root / "python_repo_maintenance")
        system_prompt = (
            f"{base_prompt}\n\n"
            f"# Skills\n\n"
            f"You have access to skills: reusable sets of instructions you can load "
            f"on demand. Before you make any edits or run any fix commands, you MUST "
            f"call the `load_skill` tool with the name of the skill that covers this "
            f"task, and then follow the instructions it returns.\n\n"
            f"Available skills:\n"
            f"- {skill.name}: {skill.description}"
        )
        return (
            SessionSpec(
                condition_name="C_skill",
                system_prompt=system_prompt,
                tools=base_tool_specs() + [load_skill_tool_spec([skill.name])],
                task_prompt=instruction,
                metadata={
                    **common,
                    "condition": "C_skill",
                    "skill_name": skill.name,
                    "skill_body_sha256": skill.body_hash,
                },
            ),
            skills_root,
        )

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        if not self.repo_root:
            await self.setup(environment)

        spec, skills_dir = self._condition_spec(instruction)
        loop = asyncio.get_running_loop()
        logs_dir = Path(self.logs_dir)
        sandbox = HarborSandbox(
            environment=environment,
            loop=loop,
            workdir=logs_dir / "workspace",
            repo_root=self.repo_root,
            base_ref=self.base_ref,
            default_timeout=self.tool_timeout_seconds,
        )
        client = get_registry().create("deepseek-flash-1017")
        started_at = datetime.now(timezone.utc).isoformat()
        recorder = EventRecorder(
            logs_dir / "events.jsonl",
            base={
                "attempt_id": logs_dir.name,
                "trial_name": logs_dir.name,
                "job_dir": logs_dir.parent.name,
                "run_id": self.run_id,
                "task_id": self.task_id,
                "repeat": self.repeat,
                "condition": spec.condition_name,
                "model_id": client.model_id,
                "agent_name": self.name(),
                "agent_version": self.version(),
                "workflow_version": spec.metadata.get("workflow_version", ""),
                "workflow_sha256": spec.metadata.get("workflow_sha256", ""),
                "system_prompt_sha256": sha256_text(spec.system_prompt),
                "task_prompt_sha256": sha256_text(spec.task_prompt),
                "repo_root": self.repo_root,
                "base_ref": self.base_ref,
                "max_steps": self.max_steps,
                "max_tokens": self.max_tokens,
                "elapsed_seconds": self.elapsed_seconds,
                "started_at": started_at,
            },
        )
        executor = ToolExecutor(
            sandbox=sandbox,
            skills_dir=skills_dir,
            tool_timeout_seconds=self.tool_timeout_seconds,
            event_sink=recorder,
        )
        try:
            # AgentLoop is synchronous; the Harbor environment remains usable
            # because the event loop is free while this worker thread blocks.
            result = await asyncio.to_thread(
                AgentLoop(
                    client,
                    executor,
                    max_steps=self.max_steps,
                    max_tokens=self.max_tokens,
                    elapsed_seconds=self.elapsed_seconds,
                    event_sink=recorder,
                ).run,
                spec,
                SimpleNamespace(
                    repo="",
                    base_commit=self.base_ref,
                    problem_statement=instruction,
                ),
            )

            patch_path = logs_dir / "patch.diff"
            patch_path.write_text(result.patch, encoding="utf-8")
            messages_path = logs_dir / "messages.jsonl"
            with messages_path.open("w", encoding="utf-8") as fh:
                for message in result.messages:
                    fh.write(json.dumps(asdict(message)) + "\n")

            context.n_input_tokens = result.usage.input_tokens
            context.n_output_tokens = result.usage.output_tokens
            if hasattr(context, "n_cache_tokens"):
                context.n_cache_tokens = result.usage.cache_read_tokens
            context.metadata = {
                "condition": spec.condition_name,
                "workflow_version": spec.metadata.get("workflow_version", ""),
                "workflow_sha256": spec.metadata.get("workflow_sha256", ""),
                "system_prompt_sha256": sha256_text(spec.system_prompt),
                "task_prompt_sha256": sha256_text(spec.task_prompt),
                "task_id": self.task_id,
                "repeat": self.repeat,
                "steps": result.steps,
                "stop_reason": result.stop_reason,
                "tool_call_count": result.tool_call_count,
                "skill_discovered": result.skill_discovered,
                "skill_loaded": result.skill_loaded,
                "errors": result.errors,
                "patch_chars": len(result.patch),
                "elapsed_seconds": round(result.elapsed_seconds, 3),
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "cache_read_tokens": result.usage.cache_read_tokens,
                "cache_write_tokens": result.usage.cache_write_tokens,
                "reasoning_tokens": result.usage.reasoning_tokens,
                "event_log": str(logs_dir / "events.jsonl"),
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            client.close()
            recorder.close()
