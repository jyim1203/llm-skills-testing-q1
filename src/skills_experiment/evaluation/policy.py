"""Failure-handling policy (handoff section 11: "define how runtime failures are
handled").

Every attempt ends in exactly one ``evaluation_status``:

======================  =================================================  =========
status                  meaning                                            rerun?
======================  =================================================  =========
``resolved``            the patch passed the benchmark's tests.            no
``unresolved``          graded and failed (agent-attributable).            no
``infrastructure_error`` setup/model/harness failure, not the patch.        yes
``not_evaluated``       produced a patch but not graded yet.               n/a
``agent_error``         the agent loop crashed before producing a patch.    yes
======================  =================================================  =========

Rationale
---------
* **Patch-apply failures count as unresolved**, because producing a patch that
  will not apply is an agent failure, not a flaky environment.
* **Empty patches count as unresolved** (the agent failed to make a change).
* **Image pulls, apply-to-container crashes, and test timeouts** are
  infrastructure errors; they are excluded from the resolved-rate denominator
  and retried under the rerun policy below.

Rerun policy
------------
An ``infrastructure_error`` attempt may be rerun at most ``max_reruns`` times
(configurable). The rerun is recorded as a *new* attempt with its own
``attempt_number`` and row, so nothing is overwritten; the original row keeps its
status. ``resolved``/``unresolved`` attempts are never rerun.
"""

from __future__ import annotations

from dataclasses import dataclass

from .harness import HarnessResult

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
INFRASTRUCTURE_ERROR = "infrastructure_error"
NOT_EVALUATED = "not_evaluated"
AGENT_ERROR = "agent_error"

RERUNNABLE_STATUSES = {INFRASTRUCTURE_ERROR, AGENT_ERROR}
COUNTED_STATUSES = {RESOLVED, UNRESOLVED}  # denominator for resolved rate

# Failure categories used in the run log's `failure_category` column.
_PATCH_APPLY_MARKERS = ("apply", "patch")


@dataclass
class Classification:
    status: str
    category: str = ""


def classify_harness_result(prediction_patch: str, instance_id: str, result: HarnessResult) -> Classification:
    """Map a harness outcome for one instance into our status + category."""
    patch = (prediction_patch or "").strip()
    if not patch and instance_id in result.empty_patch_ids:
        return Classification(UNRESOLVED, "empty_patch")

    if instance_id in result.resolved_ids:
        return Classification(RESOLVED, "")

    reason = result.failure_reasons.get(instance_id, "")

    if instance_id in result.infra_failure_ids:
        return Classification(INFRASTRUCTURE_ERROR, reason or "infra_failure")

    if instance_id in result.error_ids:
        lowered = reason.lower()
        if any(marker in lowered for marker in _PATCH_APPLY_MARKERS):
            return Classification(UNRESOLVED, "patch_apply_fail")
        return Classification(INFRASTRUCTURE_ERROR, reason or "harness_error")

    if instance_id in result.unresolved_ids:
        return Classification(UNRESOLVED, "tests_failed")

    # Not present anywhere: treat as infrastructure rather than a silent pass/fail.
    return Classification(INFRASTRUCTURE_ERROR, "not_in_report")


def should_rerun(status: str, reruns_so_far: int, max_reruns: int) -> bool:
    return status in RERUNNABLE_STATUSES and reruns_so_far < max_reruns
