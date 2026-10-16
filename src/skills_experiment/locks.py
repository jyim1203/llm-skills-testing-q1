"""Environment image locks.

Reproducibility requires that a run use the *exact* environment it claims. The
SWE-bench per-instance images are referenced by a mutable ``:latest`` tag, so the
tag name alone does not pin the environment. A lock records the immutable digest
each instance resolved to; runs refuse to start if a tag now resolves to a
different digest (or is missing), which is what makes "same environment between
runs" enforceable rather than merely documented.

The lock lives at ``data/image_locks/<experiment_id>.json`` and is meant to be
committed. Create or refresh it with::

    python -m skills_experiment preflight --experiment pilot --write-lock
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import paths


class ImageLockError(RuntimeError):
    """Raised when local images do not match the recorded lock."""


def _lock_dir(data_dir: Optional[Path] = None) -> Path:
    return (Path(data_dir) if data_dir else paths.DATA_DIR) / "image_locks"


def lock_path(experiment_id: str, data_dir: Optional[Path] = None) -> Path:
    return _lock_dir(data_dir) / f"{experiment_id}.json"


@dataclass
class ImageLock:
    """The digest every task image resolved to when the lock was written."""

    experiment_id: str
    dataset_revision: str = ""
    created_at: str = ""
    # instance_id -> {"image": <tag>, "digest": <registry digest>}
    images: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "dataset_revision": self.dataset_revision,
            "created_at": self.created_at,
            "images": self.images,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageLock":
        return cls(
            experiment_id=data.get("experiment_id", ""),
            dataset_revision=data.get("dataset_revision", ""),
            created_at=data.get("created_at", ""),
            images=dict(data.get("images", {})),
        )


def load_lock(experiment_id: str, data_dir: Optional[Path] = None) -> Optional[ImageLock]:
    path = lock_path(experiment_id, data_dir)
    if not path.exists():
        return None
    return ImageLock.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_lock(lock: ImageLock, data_dir: Optional[Path] = None) -> Path:
    path = lock_path(lock.experiment_id, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not lock.created_at:
        lock.created_at = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(lock.to_dict(), indent=2), encoding="utf-8")
    return path


def verify(lock: ImageLock, resolved: dict[str, str]) -> list[str]:
    """Return human-readable problems (empty list == everything matches).

    ``resolved`` maps ``instance_id -> locally resolved digest`` (``""`` when the
    image is not present locally).
    """
    problems: list[str] = []
    for instance_id, entry in sorted(lock.images.items()):
        expected = entry.get("digest", "")
        actual = resolved.get(instance_id, "")
        if not actual:
            problems.append(
                f"{instance_id}: image not present locally (expected "
                f"{entry.get('image', '?')} @ {expected[:19]}...); run `preflight`"
            )
        elif expected and actual != expected:
            problems.append(
                f"{instance_id}: digest mismatch -- lock {expected}, local {actual}"
            )
    for instance_id in sorted(resolved):
        if instance_id not in lock.images:
            problems.append(f"{instance_id}: not covered by the image lock (lock is stale)")
    return problems
