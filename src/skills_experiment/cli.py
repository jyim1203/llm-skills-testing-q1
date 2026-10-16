"""Command-line interface.

    python -m skills_experiment list-models
    python -m skills_experiment build-skill
    python -m skills_experiment select-tasks [--dev] [--cache]
    python -m skills_experiment plan --experiment pilot
    python -m skills_experiment run --experiment pilot [--dry-run] [--limit N] [--grade]
    python -m skills_experiment grade --experiment pilot-dev [--condition C_skill]
    python -m skills_experiment rerun --experiment pilot
    python -m skills_experiment analyze --experiment pilot
    python -m skills_experiment smoke
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from . import __version__, paths
from .analysis import analyze, load_records, render_text
from .benchmark import selection as selection_mod
from .benchmark import swebench_lite
from .config import load_experiment
from .evaluation import HarnessError, grade_experiment
from .models.registry import get_registry
from .runlog import RunLogger
from .runner import ExperimentRunner
from .skills import ensure_skill_built


def _base_dir(args: argparse.Namespace) -> Optional[Path]:
    value = getattr(args, "base_dir", "") or ""
    return Path(value) if value else None


def _resolve_experiment_id(name: str) -> str:
    """Accept either an experiment config name (file) or a raw experiment id."""
    matches = list(paths.EXPERIMENTS_DIR.glob(f"{name}.toml"))
    if matches:
        return load_experiment(name).id
    return name


def _cmd_list_models(args: argparse.Namespace) -> int:
    registry = get_registry()
    print(f"Model profiles ({paths.MODELS_DIR}):")
    for profile in registry.profiles():
        print("  " + profile.summary())
    print("\nSwap models by changing `model = \"<name>\"` in the experiment config.")
    return 0


def _cmd_build_skill(args: argparse.Namespace) -> int:
    workflow = (paths.PROMPTS_DIR / "workflow_instructions.md").read_text(encoding="utf-8")
    skill = ensure_skill_built(workflow)
    print(f"Wrote {skill.path}")
    print(f"  name:    {skill.name}")
    print(f"  body:    sha256={skill.body_hash}")
    print(f"  chars:   {len(skill.body)}")
    return 0


def _cmd_select_tasks(args: argparse.Namespace) -> int:
    subset = "dev" if getattr(args, "dev", False) else "main"
    path = selection_mod.write_selection(subset=subset)
    print(f"Wrote selection -> {path}")
    ids = (
        selection_mod.dev_instance_ids()
        if subset == "dev"
        else selection_mod.selected_instance_ids()
    )
    print(f"Selected {len(ids)} instances ({subset}): {', '.join(ids)}")
    if args.cache:
        split = "dev" if subset == "dev" else "test"
        for iid in ids:
            task = swebench_lite.load_instance(iid, split=split, offline=False)
            print(f"  cached {iid} ({task.repo})")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    config = load_experiment(args.experiment)
    runner = ExperimentRunner(config, dry_run=args.dry_run)
    assets = runner._load_assets()
    fairness = runner.verify_fairness(assets)
    tasks = runner._load_tasks()
    plan = runner.build_plan([t["task"].instance_id for t in tasks])
    print(f"Experiment : {config.id}")
    print(f"Model      : {'mock (dry-run)' if args.dry_run else config.model}")
    print(f"Conditions : {config.conditions}")
    print(f"Repeats    : {config.repeats}")
    print(f"Dataset    : {config.dataset.name}:{config.dataset.split}")
    print(f"Sandbox    : {config.sandbox.kind}")
    print(f"Tasks      : {len(tasks)}")
    for entry in tasks:
        t = entry["task"]
        print(f"  - {t.instance_id:<32} [{entry['topic']}]")
    print(f"Planned runs: {len(plan)}")
    if fairness:
        print(f"Fairness hashes: {json.dumps(fairness)}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_experiment(args.experiment)
    model = getattr(args, "model", "") or ""
    if model:
        config.model = model
    dry_run = bool(getattr(args, "dry_run", False))
    limit = int(getattr(args, "limit", 0) or 0)

    runner = ExperimentRunner(config, dry_run=dry_run, base_dir=_base_dir(args))
    summary = _run_with_limit(runner, limit)
    print(json.dumps(summary.as_dict(), indent=2))
    print(f"\nArtifacts: {runner.logger.base_dir}")

    if getattr(args, "grade", False):
        print("\nGrading with the SWE-bench harness ...")
        grade = grade_experiment(
            config,
            base_dir=_base_dir(args),
            max_workers=config.harness.max_workers,
        )
        print(json.dumps(grade.as_dict(), indent=2))
    return 0


def _run_with_limit(runner: ExperimentRunner, limit: Optional[int]):
    if not limit:
        return runner.run()

    original = runner._load_tasks

    def limited():
        return original()[:limit]

    runner._load_tasks = limited  # type: ignore[assignment]
    return runner.run()


def _cmd_grade(args: argparse.Namespace) -> int:
    config = load_experiment(args.experiment)
    try:
        summary = grade_experiment(
            config,
            base_dir=_base_dir(args),
            only_missing=not args.regrade,
            condition=args.condition or None,
            attempt=args.attempt,
            max_workers=args.max_workers or config.harness.max_workers,
            timeout=args.timeout or None,
        )
    except HarnessError as exc:
        print(f"grading failed: {exc}")
        return 2
    print(json.dumps(summary.as_dict(), indent=2))
    return 0


def _cmd_rerun(args: argparse.Namespace) -> int:
    config = load_experiment(args.experiment)
    runner = ExperimentRunner(config, dry_run=args.dry_run, base_dir=_base_dir(args))
    summary = runner.rerun(max_reruns=args.max_reruns)
    print(json.dumps(summary.as_dict(), indent=2))
    print(f"\nArtifacts: {runner.logger.base_dir}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    experiment_id = _resolve_experiment_id(args.experiment)
    records = load_records(experiment_id, _base_dir(args))
    if not records:
        print(f"No run log for experiment '{experiment_id}'.")
        return 2
    summary = analyze(
        records,
        reference=args.reference or None,
        n_resamples=args.resamples,
    )
    print(render_text(summary))
    if args.json:
        print(json.dumps(summary, indent=2))
    logger = RunLogger(experiment_id, _base_dir(args) or paths.RUNS_DIR)
    out = logger.base_dir / "analysis.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


def _cmd_smoke(args: argparse.Namespace) -> int:
    """End-to-end dry run on a single task using the mock model + noop sandbox."""
    args.experiment = args.experiment or "pilot"
    args.dry_run = True
    args.model = "mock"
    args.limit = 1
    args.grade = False
    return _cmd_run(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skills-exp",
        description="Skills-vs-prompt experiment tooling (SWE-bench Lite).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list-models", help="List model profiles.")
    p.set_defaults(func=_cmd_list_models)

    p = sub.add_parser("build-skill", help="Regenerate SKILL.md from the workflow file.")
    p.set_defaults(func=_cmd_build_skill)

    p = sub.add_parser("select-tasks", help="Write the frozen task selection.")
    p.add_argument("--dev", action="store_true", help="Write the dev/smoke subset instead.")
    p.add_argument("--cache", action="store_true", help="Also download+cache the instances.")
    p.set_defaults(func=_cmd_select_tasks)

    p = sub.add_parser("plan", help="Print the run matrix without running.")
    p.add_argument("--experiment", default="pilot")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=_cmd_plan)

    p = sub.add_parser("run", help="Run an experiment.")
    p.add_argument("--experiment", default="pilot")
    p.add_argument("--model", default="", help="Override the model profile name.")
    p.add_argument("--dry-run", action="store_true", help="Use the mock model + noop sandbox.")
    p.add_argument("--limit", type=int, default=0, help="Only run the first N tasks.")
    p.add_argument("--base-dir", default="", help="Output directory (default: runs/).")
    p.add_argument("--grade", action="store_true", help="Grade with the harness after running.")
    p.set_defaults(func=_cmd_run)

    p = sub.add_parser("grade", help="Grade captured patches with the SWE-bench harness.")
    p.add_argument("--experiment", default="pilot")
    p.add_argument("--condition", default="", help="Only grade this condition.")
    p.add_argument("--attempt", type=int, default=None, help="Only grade this attempt number.")
    p.add_argument("--max-workers", type=int, default=0, help="Harness parallelism.")
    p.add_argument("--timeout", type=int, default=0, help="Per-instance test timeout (s).")
    p.add_argument("--regrade", action="store_true", help="Re-grade attempts already resolved/unresolved.")
    p.add_argument("--base-dir", default="")
    p.set_defaults(func=_cmd_grade)

    p = sub.add_parser("rerun", help="Re-run attempts that failed for infrastructure reasons.")
    p.add_argument("--experiment", default="pilot")
    p.add_argument("--max-reruns", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--base-dir", default="")
    p.set_defaults(func=_cmd_rerun)

    p = sub.add_parser("analyze", help="Summarize a run log.")
    p.add_argument("--experiment", default="pilot")
    p.add_argument("--reference", default="", help="Reference condition for effects (default: first).")
    p.add_argument("--resamples", type=int, default=5000, help="Bootstrap resamples.")
    p.add_argument("--json", action="store_true", help="Also print the raw JSON summary.")
    p.add_argument("--base-dir", default="")
    p.set_defaults(func=_cmd_analyze)

    p = sub.add_parser("smoke", help="Single-task dry run with the mock model.")
    p.add_argument("--experiment", default="pilot")
    p.set_defaults(func=_cmd_smoke)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
