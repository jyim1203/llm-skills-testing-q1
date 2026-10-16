"""skills_experiment

Tooling for the study: *does delivering a workflow as an agent Skill differ
from pasting the same instructions into the prompt?*

Top-level pieces
----------------
models/      provider-agnostic model clients + TOML-driven registry (swap models
             by changing one config value)
conditions/  the three experimental conditions (A baseline, B direct prompt,
             C skill) as isolated, comparable session builders
agent/       a minimal tool-using agent loop
sandbox/     where the agent's commands actually run (local / docker)
benchmark/   SWE-bench Lite loading and task selection
runlog/      one row per attempt, matching the handoff run-log schema
runner.py    orchestrates tasks x conditions x repeats with full isolation
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
