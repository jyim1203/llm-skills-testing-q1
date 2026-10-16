"""SWE-bench Lite loading.

We avoid a hard dependency on the ``datasets`` library by reading records from
the HuggingFace *datasets-server* REST API and caching them as JSON under
``data/instances/``. This keeps setup light while remaining reproducible: the
cache is keyed by instance id and can be committed or regenerated.

The gold ``patch`` and ``test_patch`` are Eval-only. They are stored in the
cache for grading/auditing but must never reach the agent -- see
:meth:`TaskInstance.agent_view`.
"""

from __future__ import annotations

import ast
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from .. import paths

DEFAULT_DATASET = "SWE-bench/SWE-bench_Lite"
_DATASETS_SERVER = "https://datasets-server.huggingface.co/rows"


class BenchmarkError(RuntimeError):
    """Raised for dataset loading problems."""


@dataclass
class TaskInstance:
    """One SWE-bench Lite instance.

    Field names mirror the upstream dataset. ``patch`` and ``test_patch`` are
    evaluation-only and are deliberately excluded from :meth:`agent_view`.
    """

    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    hints_text: str = ""
    version: str = ""
    environment_setup_commit: str = ""
    image: str = ""
    created_at: str = ""
    difficulty: str = ""
    eval_type: str = ""
    log_parser: str = ""
    eval_script: str = ""
    FAIL_TO_PASS: list[str] = field(default_factory=list)
    PASS_TO_PASS: list[str] = field(default_factory=list)
    # eval-only
    patch: str = ""
    test_patch: str = ""

    # -- serialization ------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskInstance":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})  # type: ignore[arg-type]

    # -- agent-visible projection ------------------------------------------- #
    def agent_view(self) -> dict[str, str]:
        """Return ONLY the fields the agent may see (no gold/test patches)."""
        return {
            "instance_id": self.instance_id,
            "repo": self.repo,
            "problem_statement": self.problem_statement,
            "hints_text": self.hints_text,
        }


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def _parse_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return [text]
    if isinstance(parsed, list):
        return [str(v) for v in parsed]
    return [str(parsed)]


def _row_to_task(row: dict[str, Any]) -> TaskInstance:
    return TaskInstance(
        instance_id=row["instance_id"],
        repo=row["repo"],
        base_commit=row["base_commit"],
        problem_statement=row.get("problem_statement", ""),
        hints_text=row.get("hints_text", "") or "",
        version=str(row.get("version", "")),
        environment_setup_commit=row.get("environment_setup_commit", "") or "",
        image=row.get("image", "") or "",
        created_at=row.get("created_at", "") or "",
        difficulty=row.get("difficulty", "") or "",
        eval_type=row.get("eval_type", "") or "",
        log_parser=row.get("log_parser", "") or "",
        eval_script=row.get("eval_script", "") or "",
        FAIL_TO_PASS=_parse_list_field(row.get("FAIL_TO_PASS")),
        PASS_TO_PASS=_parse_list_field(row.get("PASS_TO_PASS")),
        patch=row.get("patch", "") or "",
        test_patch=row.get("test_patch", "") or "",
    )


# --------------------------------------------------------------------------- #
# Fetching + caching
# --------------------------------------------------------------------------- #
def _http_get_json(url: str, retries: int = 3, timeout: int = 60) -> dict[str, Any]:
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise BenchmarkError(f"Failed to fetch {url!r}: {last_exc}")


def fetch_rows(
    dataset: str = DEFAULT_DATASET, split: str = "test", page_size: int = 100
) -> list[dict[str, Any]]:
    """Fetch every row for a dataset split from the datasets-server."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode(
            {
                "dataset": dataset,
                "config": "default",
                "split": split,
                "offset": offset,
                "length": page_size,
            }
        )
        payload = _http_get_json(f"{_DATASETS_SERVER}?{params}")
        page = payload.get("rows", [])
        rows.extend(r["row"] for r in page)
        total = payload.get("num_rows_total", len(rows))
        if not page or len(rows) >= total:
            break
        offset += page_size
    return rows


def load_instance(
    instance_id: str,
    *,
    cache_dir: Optional[Path] = None,
    dataset: str = DEFAULT_DATASET,
    split: str = "test",
    offline: bool = False,
) -> TaskInstance:
    """Load one instance, preferring the local JSON cache."""
    cache_dir = cache_dir or paths.INSTANCES_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{instance_id}.json"

    if cache_file.exists():
        return TaskInstance.from_dict(json.loads(cache_file.read_text(encoding="utf-8")))

    if offline:
        raise BenchmarkError(
            f"Instance {instance_id} is not cached at {cache_file} and offline=True."
        )

    for row in fetch_rows(dataset=dataset, split=split):
        if row.get("instance_id") == instance_id:
            task = _row_to_task(row)
            cache_file.write_text(json.dumps(task.to_dict(), indent=2), encoding="utf-8")
            return task
    raise BenchmarkError(f"Instance {instance_id} not found in {dataset}:{split}.")


def load_instances(
    instance_ids: list[str],
    *,
    cache_dir: Optional[Path] = None,
    dataset: str = DEFAULT_DATASET,
    split: str = "test",
    offline: bool = False,
) -> list[TaskInstance]:
    return [
        load_instance(
            iid,
            cache_dir=cache_dir,
            dataset=dataset,
            split=split,
            offline=offline,
        )
        for iid in instance_ids
    ]


def load_selection(selection_file: str | Path) -> dict[str, Any]:
    path = Path(selection_file)
    if not path.is_absolute():
        path = paths.REPO_ROOT / path
    if not path.exists():
        raise BenchmarkError(
            f"Selection file not found: {path}. "
            f"Run `python -m skills_experiment select-tasks` to create it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def selection_instance_ids(selection_file: str | Path) -> list[str]:
    data = load_selection(selection_file)
    return [t["instance_id"] for t in data["tasks"]]
