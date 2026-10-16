"""Experiment orchestration.

Runs the matrix ``tasks x conditions x repeats`` with strict isolation:

* every attempt gets its own workspace directory and its own sandbox;
* every attempt builds a fresh message history from scratch;
* Condition C's skill file is written into that attempt's own skills directory,
  so it is invisible to A and B.

Only the intended intervention varies across conditions. Fairness (B and C use
identical instruction text) is asserted before any run starts.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import __version__, paths
from .agent.loop import AgentLoop
from .agent.tools import ToolExecutor
from .benchmark import swebench_lite
from .config import ExperimentConfig, load_condition_configs
from .conditions import ConditionAssets, ConditionContext, get_condition
from .evaluation import policy
from .models.registry import ModelRegistry, get_registry
from .runlog import RunLogger, RunRecord
from .sandbox import make_sandbox
from .skills import ensure_skill_built, sha256_text


@dataclass
class RunPlanItem:
    instance_id: str
    condition: str
    attempt: int
    run_order: int


@dataclass
class RunSummary:
    experiment_id: str
    model: str
    dry_run: bool
    planned: int = 0
    completed: int = 0
    infrastructure_errors: int = 0
    by_condition: dict[str, int] = field(default_factory=dict)
    records: list[RunRecord] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "model": self.model,
            "dry_run": self.dry_run,
            "planned": self.planned,
            "completed": self.completed,
            "infrastructure_errors": self.infrastructure_errors,
            "by_condition": self.by_condition,
        }


@dataclass
class _RunContext:
    model_name: str
    profile: Any
    client: Any
    fairness: dict[str, Any]
    conditions: dict[str, Any]
    task_by_id: dict[str, dict[str, Any]]


class ExperimentRunner:
    def __init__(
        self,
        config: ExperimentConfig,
        *,
        dry_run: bool = False,
        base_dir: Optional[Path] = None,
        registry: Optional[ModelRegistry] = None,
        client: Any = None,
    ) -> None:
        self.config = config
        self.dry_run = dry_run
        self.registry = registry or get_registry()
        self.base_dir = base_dir or paths.RUNS_DIR
        self._client = client  # optional injected client (tests)
        self.logger = RunLogger(config.id, self.base_dir)

    # -- setup -------------------------------------------------------------- #
    def _resolve_model_name(self) -> str:
        return "mock" if self.dry_run else self.config.model

    def _make_client(self):
        if self._client is not None:
            return self._client
        return self.registry.create(self._resolve_model_name())

    def _load_assets(self) -> ConditionAssets:
        base_prompt = (paths.PROMPTS_DIR / self.config.agent.base_system_prompt).read_text(
            encoding="utf-8"
        )
        workflow_file = self._workflow_file()
        workflow_text = workflow_file.read_text(encoding="utf-8") if workflow_file else ""
        skill = ensure_skill_built(workflow_text) if workflow_text else None
        return ConditionAssets(
            base_system_prompt=base_prompt,
            workflow_instructions=workflow_text,
            skill=skill,
        )

    def _workflow_file(self) -> Optional[Path]:
        for name in self.config.conditions:
            cfg = load_condition_configs([name])[0]
            if cfg.instructions_file:
                return paths.PROMPTS_DIR / cfg.instructions_file
        return None

    def verify_fairness(self, assets: ConditionAssets) -> dict[str, Any]:
        """Assert that B and C use byte-identical instruction text."""
        hashes: dict[str, Optional[str]] = {}
        for name in self.config.conditions:
            cfg = load_condition_configs([name])[0]
            if cfg.impl == "prompt_instructions":
                hashes["B"] = sha256_text(assets.workflow_instructions.strip())
            elif cfg.impl == "skill":
                if assets.skill is None:
                    raise AssertionError("Condition C requires a skill asset.")
                hashes["C"] = sha256_text(assets.skill.body.strip())
        if "B" in hashes and "C" in hashes and hashes["B"] != hashes["C"]:
            raise AssertionError(
                "Fairness check failed: Condition B prompt text and Condition C skill "
                f"body differ (B={hashes['B']}, C={hashes['C']})."
            )
        return hashes

    def _load_tasks(self) -> list[dict[str, Any]]:
        selection = swebench_lite.load_selection(self.config.dataset.selection_file)
        tasks_meta = {t["instance_id"]: t for t in selection["tasks"]}
        instances = swebench_lite.load_instances(
            list(tasks_meta),
            dataset=self.config.dataset.name,
            split=self.config.dataset.split,
            offline=self.config.dataset.offline,
        )
        merged: list[dict[str, Any]] = []
        for task in instances:
            meta = tasks_meta.get(task.instance_id, {})
            merged.append({"task": task, "topic": meta.get("topic", ""), "why": meta.get("why", "")})
        return merged

    def _prepare(self) -> _RunContext:
        model_name = self._resolve_model_name()
        profile = self.registry.get(model_name)
        client = self._make_client()
        assets = self._load_assets()
        fairness = self.verify_fairness(assets)
        conditions = {
            cc.name: get_condition(cc, assets)
            for cc in load_condition_configs(self.config.conditions)
        }
        tasks = self._load_tasks()
        return _RunContext(
            model_name=model_name,
            profile=profile,
            client=client,
            fairness=fairness,
            conditions=conditions,
            task_by_id={t["task"].instance_id: t for t in tasks},
        )

    # -- planning ----------------------------------------------------------- #
    def build_plan(self, task_ids: list[str]) -> list[RunPlanItem]:
        rng = random.Random(self.config.seed)
        plan: list[RunPlanItem] = []
        order = 0
        for instance_id in task_ids:
            conditions = list(self.config.conditions)
            if self.config.interleave:
                conditions = sorted(conditions)
                rng.shuffle(conditions)
            for condition in conditions:
                for attempt in range(1, self.config.repeats + 1):
                    order += 1
                    plan.append(
                        RunPlanItem(
                            instance_id=instance_id,
                            condition=condition,
                            attempt=attempt,
                            run_order=order,
                        )
                    )
        return plan

    # -- execution ---------------------------------------------------------- #
    def run(self) -> RunSummary:
        if self.config.fresh:
            self.logger.reset()
        ctx = self._prepare()
        plan = self.build_plan(list(ctx.task_by_id))
        summary = self.run_plan(plan, ctx)
        if hasattr(ctx.client, "close"):
            ctx.client.close()
        return summary

    def run_plan(self, plan: list[RunPlanItem], ctx: _RunContext) -> RunSummary:
        summary = RunSummary(
            experiment_id=self.config.id, model=ctx.model_name, dry_run=self.dry_run, planned=len(plan)
        )
        for item in plan:
            task_entry = ctx.task_by_id.get(item.instance_id)
            if task_entry is None:
                continue
            record = self._run_item(
                item=item,
                task_entry=task_entry,
                condition=ctx.conditions[item.condition],
                client=ctx.client,
                profile=ctx.profile,
                fairness=ctx.fairness,
            )
            summary.records.append(record)
            summary.completed += 1
            if record.evaluation_status == policy.INFRASTRUCTURE_ERROR:
                summary.infrastructure_errors += 1
            summary.by_condition[record.condition] = summary.by_condition.get(record.condition, 0) + 1
        return summary

    def rerun(self, *, max_reruns: int = 1) -> RunSummary:
        """Re-run attempts that ended in a rerunnable failure.

        New attempts are appended with their own ``attempt_number``; existing
        rows are never overwritten. Attempts that already produced a patch are
        re-graded (see the ``grade`` command) rather than re-run.
        """
        records = self.logger.load_records()
        if not records:
            return RunSummary(self.config.id, self._resolve_model_name(), self.dry_run)

        by_key: dict[tuple[str, str], list[RunRecord]] = defaultdict(list)
        for rec in records:
            by_key[(rec.instance_id, rec.condition)].append(rec)

        ctx = self._prepare()
        order = max((r.run_order for r in records), default=0)
        plan: list[RunPlanItem] = []
        for (instance_id, condition), recs in sorted(by_key.items()):
            latest = max(recs, key=lambda r: r.attempt_number)
            extra_attempts = len(recs) - self.config.repeats
            has_patch = bool(latest.patch_path and Path(latest.patch_path).exists() and Path(latest.patch_path).read_text(encoding="utf-8").strip())
            if policy.should_rerun(latest.evaluation_status, extra_attempts, max_reruns) and not has_patch:
                order += 1
                plan.append(
                    RunPlanItem(
                        instance_id=instance_id,
                        condition=condition,
                        attempt=latest.attempt_number + 1,
                        run_order=order,
                    )
                )
        summary = self.run_plan(plan, ctx)
        if hasattr(ctx.client, "close"):
            ctx.client.close()
        return summary

    def _run_item(
        self,
        *,
        item: RunPlanItem,
        task_entry: dict[str, Any],
        condition,
        client: Any,
        profile,
        fairness: dict[str, Any],
    ) -> RunRecord:
        task = task_entry["task"]
        workdir = self.logger.workspace_dir(item.instance_id, item.condition, item.attempt)
        skills_dir = workdir / "skills"

        record = RunRecord(
            experiment_id=self.config.id,
            condition=item.condition,
            model_id=profile.model_id,
            agent_framework_version=__version__,
            benchmark_dataset_id=self.config.dataset.name,
            benchmark_dataset_revision=self.config.dataset.revision,
            split=self.config.dataset.split,
            instance_id=item.instance_id,
            repo=task.repo,
            topic=task_entry.get("topic", ""),
            attempt_number=item.attempt,
            run_order=item.run_order,
            max_steps=self.config.budgets.max_steps,
            max_tokens=self.config.budgets.max_tokens,
            harness_version=self._harness_version(),
            skill_version_or_hash=fairness.get("C", "") if fairness else "",
            prompt_version_or_hash=fairness.get("B", "") if fairness else "",
        )

        sandbox = None
        try:
            sandbox = self._make_sandbox(workdir)
            sandbox.prepare(task)
            ctx = ConditionContext(task=task, workspace=workdir, skills_dir=skills_dir)
            spec = condition.build(ctx)
            executor = ToolExecutor(
                sandbox=sandbox,
                skills_dir=skills_dir,
                tool_timeout_seconds=self.config.budgets.tool_timeout_seconds,
            )
            loop = AgentLoop(
                client,
                executor,
                max_steps=self.config.budgets.max_steps,
                max_tokens=self.config.budgets.max_tokens,
                elapsed_seconds=self.config.budgets.elapsed_seconds,
            )
            result = loop.run(spec, task=task)

            record.input_tokens = result.usage.input_tokens
            record.output_tokens = result.usage.output_tokens
            record.total_tokens = result.usage.total_tokens
            record.tool_call_count = result.tool_call_count
            record.steps = result.steps
            record.elapsed_seconds = round(result.elapsed_seconds, 3)
            record.stop_reason = result.stop_reason
            record.skill_discovered = result.skill_discovered
            record.skill_loaded = result.skill_loaded
            record.evaluation_status = policy.NOT_EVALUATED
            if result.errors:
                record.notes = f"tool errors: {len(result.errors)}"

            patch_path = self.logger.save_artifacts(
                record,
                patch=result.patch,
                messages=result.messages,
                condition_metadata=spec.metadata,
                result_extra={
                    "stop_reason": result.stop_reason,
                    "steps": result.steps,
                    "errors": result.errors,
                },
            )
            record.patch_path = patch_path

        except Exception as exc:  # noqa: BLE001 - infrastructure failures are data
            record.evaluation_status = policy.INFRASTRUCTURE_ERROR
            record.failure_category = type(exc).__name__
            record.notes = f"{type(exc).__name__}: {exc}"
        finally:
            if sandbox is not None:
                sandbox.cleanup()

        self.logger.append(record)
        return record

    def _make_sandbox(self, workdir: Path):
        kind = "noop" if self.dry_run else self.config.sandbox.kind
        kwargs: dict[str, Any] = {}
        if kind == "docker":
            kwargs["image_template"] = self.config.sandbox.docker_image_template
        return make_sandbox(kind, workdir, **kwargs)

    @staticmethod
    def _harness_version() -> str:
        try:
            import importlib.metadata as md

            return md.version("swebench")
        except Exception:  # noqa: BLE001 - optional dependency
            return ""
