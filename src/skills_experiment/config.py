"""Configuration loading.

All configuration uses TOML and the standard-library ``tomllib`` parser, so the
core framework has **zero third-party dependencies**. This is deliberate: it
keeps setup friction low and makes ``pip install -e .`` optional for the parts
that do not call a real model.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import paths


def load_toml(path: str | Path) -> dict[str, Any]:
    """Read a TOML file into a plain dict."""
    p = Path(path)
    with p.open("rb") as fh:
        return tomllib.load(fh)


# --------------------------------------------------------------------------- #
# Condition configuration
# --------------------------------------------------------------------------- #
@dataclass
class ConditionConfig:
    name: str
    impl: str
    instructions_file: str = ""
    skill_enabled: bool = False
    skill_name: str = ""
    skill_dir: str = ""
    # Condition C only: require the agent to call `load_skill` before editing.
    # Off by default so the frozen pilot-01 C prompt remains reproducible.
    require_load: bool = False
    notes: str = ""
    source_path: Path | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "ConditionConfig":
        data = load_toml(path)
        return cls(
            name=data["name"],
            impl=data["impl"],
            instructions_file=data.get("instructions_file", "") or "",
            skill_enabled=bool(data.get("skill_enabled", False)),
            skill_name=data.get("skill_name", "") or "",
            skill_dir=data.get("skill_dir", "") or "",
            require_load=bool(data.get("require_load", False)),
            notes=data.get("notes", "") or "",
            source_path=Path(path),
        )


def load_condition_configs(
    names: list[str],
    directory: Path | None = None,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> list[ConditionConfig]:
    """Load condition configs, optionally applying per-experiment overrides.

    ``overrides`` maps a condition name to fields that replace the values in
    that condition's TOML. This keeps a study-level change (e.g. requiring
    ``load_skill`` for a new model run) out of the shared condition file, so
    earlier frozen runs keep their original prompt.
    """
    directory = directory or paths.CONDITIONS_DIR
    overrides = overrides or {}
    configs: list[ConditionConfig] = []
    for name in names:
        matches = list(directory.glob(f"{name}.toml"))
        if not matches:
            raise FileNotFoundError(
                f"No condition config for '{name}' in {directory}"
            )
        config = ConditionConfig.from_file(matches[0])
        for key, value in overrides.get(name, {}).items():
            if not hasattr(config, key):
                raise ValueError(
                    f"Unknown condition option {key!r} for '{name}'. "
                    f"Known: {sorted(config.__dataclass_fields__)}"
                )
            setattr(config, key, value)
        configs.append(config)
    return configs


# --------------------------------------------------------------------------- #
# Experiment configuration
# --------------------------------------------------------------------------- #
@dataclass
class Budgets:
    max_steps: int = 40
    max_tokens: int = 120_000
    elapsed_seconds: int = 1800
    tool_timeout_seconds: int = 120

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Budgets":
        return cls(
            max_steps=int(d.get("max_steps", 40)),
            max_tokens=int(d.get("max_tokens", 120_000)),
            elapsed_seconds=int(d.get("elapsed_seconds", 1800)),
            tool_timeout_seconds=int(d.get("tool_timeout_seconds", 120)),
        )


@dataclass
class DatasetConfig:
    name: str = "SWE-bench/SWE-bench_Lite"
    revision: str = "main"
    split: str = "test"
    selection_file: str = "data/task_selection.json"
    offline: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DatasetConfig":
        return cls(
            name=d.get("name", "SWE-bench/SWE-bench_Lite"),
            revision=d.get("revision", "main"),
            split=d.get("split", "test"),
            selection_file=d.get("selection_file", "data/task_selection.json"),
            offline=bool(d.get("offline", False)),
        )


@dataclass
class SandboxConfig:
    kind: str = "local"
    docker_image_template: str = "swebench/sweb.eval.x86_64.{repo_slug}:latest"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SandboxConfig":
        return cls(
            kind=d.get("kind", "local"),
            docker_image_template=d.get(
                "docker_image_template", "swebench/sweb.eval.x86_64.{repo_slug}:latest"
            ),
        )


@dataclass
class AgentConfig:
    base_system_prompt: str = "base_system_prompt.md"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentConfig":
        return cls(base_system_prompt=d.get("base_system_prompt", "base_system_prompt.md"))


@dataclass
class HarnessConfig:
    """Settings for invoking the official SWE-bench evaluation harness."""

    # Interpreter used to run `swebench.harness.run_evaluation`. The harness has
    # heavy dependencies, so it is commonly a dedicated venv rather than the
    # framework's interpreter. Empty -> $SWEBENCH_PYTHON, else sys.executable.
    python: str = ""
    max_workers: int = 4
    timeout_seconds: int = 1800
    extra_args: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "HarnessConfig":
        return cls(
            python=d.get("python", "") or "",
            max_workers=int(d.get("max_workers", 4)),
            timeout_seconds=int(d.get("timeout_seconds", 1800)),
            extra_args=list(d.get("extra_args", []) or []),
        )


@dataclass
class ExperimentConfig:
    id: str
    model: str
    conditions: list[str]
    repeats: int = 1
    seed: int = 0
    interleave: bool = True
    fresh: bool = True
    budgets: Budgets = field(default_factory=Budgets)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    harness: HarnessConfig = field(default_factory=HarnessConfig)
    # Per-experiment condition overrides: {condition_name: {field: value}}.
    condition_options: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_path: Path | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "ExperimentConfig":
        data = load_toml(path)
        exp = data.get("experiment", {})
        return cls(
            id=exp["id"],
            model=exp["model"],
            conditions=list(exp["conditions"]),
            repeats=int(exp.get("repeats", 1)),
            seed=int(exp.get("seed", 0)),
            interleave=bool(exp.get("interleave", True)),
            fresh=bool(exp.get("fresh", True)),
            budgets=Budgets.from_dict(data.get("budgets", {})),
            dataset=DatasetConfig.from_dict(data.get("dataset", {})),
            sandbox=SandboxConfig.from_dict(data.get("sandbox", {})),
            agent=AgentConfig.from_dict(data.get("agent", {})),
            harness=HarnessConfig.from_dict(data.get("harness", {})),
            condition_options={
                str(name): dict(options)
                for name, options in (data.get("condition_options", {}) or {}).items()
            },
            source_path=Path(path),
        )


def load_experiment(name: str, directory: Path | None = None) -> ExperimentConfig:
    directory = directory or paths.EXPERIMENTS_DIR
    matches = list(directory.glob(f"{name}.toml"))
    if not matches:
        raise FileNotFoundError(f"No experiment config for '{name}' in {directory}")
    return ExperimentConfig.from_file(matches[0])
