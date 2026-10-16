"""Run logging.

One row per attempt, matching the handoff run-log schema (section 12). Full
artifacts (patch, message transcript, condition definition) are stored
separately under ``runs/<experiment_id>/...`` and linked by
``experiment_id / instance_id / condition / attempt_number``.

Secrets are never written here.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..models.types import Message

RUN_COLUMNS = [
    "experiment_id",
    "condition",
    "model_id",
    "agent_framework_version",
    "benchmark_dataset_id",
    "benchmark_dataset_revision",
    "split",
    "instance_id",
    "repo",
    "topic",
    "attempt_number",
    "run_order",
    "skill_version_or_hash",
    "prompt_version_or_hash",
    "max_steps",
    "max_tokens",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "input_cost_usd",
    "output_cost_usd",
    "total_cost_usd",
    "tool_call_count",
    "steps",
    "elapsed_seconds",
    "stop_reason",
    "skill_discovered",
    "skill_loaded",
    "patch_path",
    "harness_version",
    "tests_passed",
    "tests_total",
    "fail_to_pass_passed",
    "fail_to_pass_total",
    "pass_to_pass_passed",
    "pass_to_pass_total",
    "evaluation_status",
    "failure_category",
    "notes",
]


@dataclass
class RunRecord:
    experiment_id: str = ""
    condition: str = ""
    model_id: str = ""
    agent_framework_version: str = ""
    benchmark_dataset_id: str = ""
    benchmark_dataset_revision: str = ""
    split: str = ""
    instance_id: str = ""
    repo: str = ""
    topic: str = ""
    attempt_number: int = 1
    run_order: int = 0
    skill_version_or_hash: str = ""
    prompt_version_or_hash: str = ""
    max_steps: int = 0
    max_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    tool_call_count: int = 0
    steps: int = 0
    elapsed_seconds: float = 0.0
    stop_reason: str = ""
    skill_discovered: bool = False
    skill_loaded: bool = False
    patch_path: str = ""
    harness_version: str = ""
    # Test tallies from the graded run (0 when never evaluated).
    tests_passed: int = 0
    tests_total: int = 0
    fail_to_pass_passed: int = 0
    fail_to_pass_total: int = 0
    pass_to_pass_passed: int = 0
    pass_to_pass_total: int = 0
    # resolved | unresolved | infrastructure_error | not_evaluated
    evaluation_status: str = "not_evaluated"
    failure_category: str = ""
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("extra", None)
        # serialize booleans as lowercase strings for readable CSV
        for key in ("skill_discovered", "skill_loaded"):
            data[key] = str(data[key]).lower()
        return {col: data.get(col, "") for col in RUN_COLUMNS}

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class RunLogger:
    """Writes the per-attempt row plus its artifacts."""

    def __init__(self, experiment_id: str, base_dir: Path) -> None:
        self.experiment_id = experiment_id
        self.base_dir = Path(base_dir) / experiment_id
        self.work_dir = self.base_dir / "work"
        self.jsonl_path = self.base_dir / "runs.jsonl"
        self.csv_path = self.base_dir / "runs.csv"
        self.attempts_dir = self.base_dir / "attempts"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.attempts_dir.mkdir(parents=True, exist_ok=True)

    def reset(self) -> None:
        """Clear prior outputs for a fresh run of the same experiment id."""
        import shutil

        for path in (self.jsonl_path, self.csv_path):
            if path.exists():
                path.unlink()
        for directory in (self.work_dir, self.attempts_dir):
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)

    def attempt_dir(self, instance_id: str, condition: str, attempt: int) -> Path:
        path = self.attempts_dir / instance_id / condition / f"attempt_{attempt:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def workspace_dir(self, instance_id: str, condition: str, attempt: int) -> Path:
        path = self.work_dir / instance_id / condition / f"attempt_{attempt:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, record: RunRecord) -> None:
        row = record.to_row()
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_json()) + "\n")
        write_header = not self.csv_path.exists()
        with self.csv_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=RUN_COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    # -- batch read/update (used by grading and reruns) --------------------- #
    def load_records(self) -> list[RunRecord]:
        """Read every attempt row back from ``runs.jsonl``."""
        if not self.jsonl_path.exists():
            return []
        records: list[RunRecord] = []
        for line in self.jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            known = {f for f in RunRecord.__dataclass_fields__}  # type: ignore[attr-defined]
            records.append(RunRecord(**{k: v for k, v in data.items() if k in known}))
        return records

    def rewrite(self, records: list[RunRecord]) -> None:
        """Overwrite ``runs.jsonl``/``runs.csv`` in place from ``records``."""
        with self.jsonl_path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record.to_json()) + "\n")
        with self.csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=RUN_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow(record.to_row())

    def save_artifacts(
        self,
        record: RunRecord,
        *,
        patch: str = "",
        messages: Optional[list[Message]] = None,
        condition_metadata: Optional[dict[str, Any]] = None,
        result_extra: Optional[dict[str, Any]] = None,
    ) -> str:
        """Persist patch, transcript, and metadata; return the patch path."""
        directory = self.attempt_dir(
            record.instance_id, record.condition, record.attempt_number
        )

        patch_path = directory / "patch.diff"
        patch_path.write_text(patch, encoding="utf-8")

        if messages is not None:
            with (directory / "messages.jsonl").open("w", encoding="utf-8") as fh:
                for msg in messages:
                    fh.write(
                        json.dumps(
                            {
                                "role": msg.role,
                                "content": msg.content,
                                "tool_calls": [asdict(tc) for tc in msg.tool_calls],
                                "tool_call_id": msg.tool_call_id,
                                "name": msg.name,
                            }
                        )
                        + "\n"
                    )

        if condition_metadata is not None:
            (directory / "condition.json").write_text(
                json.dumps(condition_metadata, indent=2), encoding="utf-8"
            )
        if result_extra is not None:
            (directory / "result.json").write_text(
                json.dumps(result_extra, indent=2), encoding="utf-8"
            )

        return str(patch_path)
