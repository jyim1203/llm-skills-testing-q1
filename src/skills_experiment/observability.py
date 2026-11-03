"""Lightweight structured event logging for mechanism/behavior analysis.

The experiment's primary data are no longer just the final reward.  We need to
know *when* the model was called, what tools it chose, how long each call took,
and what the provider reported for token usage.  This module keeps that
instrumentation out of the model providers and the Harbor adapter.

Events are written as one JSON object per line.  The recorder is deliberately
tiny and dependency-free so it can be used from the synchronous agent thread
while Harbor's event loop is still serving container commands.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

EventSink = Callable[[str, dict[str, Any]], None]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def emit(sink: Optional[EventSink], event: str, **fields: Any) -> None:
    """Best-effort event emission; logging must never break an attempt."""
    if sink is None:
        return
    try:
        sink(event, fields)
    except Exception:  # noqa: BLE001 - observability is best-effort
        return


@dataclass
class EventRecorder:
    """Append-only JSONL event recorder.

    ``base`` fields are copied into every event (attempt, condition, model,
    hashes, budgets).  Per-event fields override base fields if they collide.
    """

    path: Path
    base: dict[str, Any] = field(default_factory=dict)
    _fh: Any = field(init=False, repr=False)
    _lock: Any = field(init=False, repr=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.base.setdefault("schema_version", "1")
        self._fh = self.path.open("a", encoding="utf-8")

    def __call__(self, event: str, fields: dict[str, Any]) -> None:
        record: dict[str, Any] = {
            "event": event,
            "timestamp": utc_now(),
            "time_unix": time.time(),
            **self.base,
            **fields,
        }
        line = json.dumps(record, default=str, ensure_ascii=False)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()

    def close(self) -> None:
        with self._lock:
            if not self._fh.closed:
                self._fh.close()
