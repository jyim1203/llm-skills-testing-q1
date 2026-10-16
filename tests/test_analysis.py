"""Analysis: per-condition stats and paired task-level effects."""

from __future__ import annotations

from skills_experiment.analysis import analyze, condition_stats, paired_effect, render_text
from skills_experiment.evaluation import policy
from skills_experiment.runlog import RunRecord


def _rec(cond: str, iid: str, status: str, tokens: int = 0) -> RunRecord:
    return RunRecord(condition=cond, instance_id=iid, evaluation_status=status, total_tokens=tokens)


def _matrix() -> list[RunRecord]:
    return [
        _rec("A_baseline", "t1", policy.UNRESOLVED),
        _rec("A_baseline", "t2", policy.UNRESOLVED),
        _rec("B_prompt_instructions", "t1", policy.UNRESOLVED),
        _rec("B_prompt_instructions", "t2", policy.RESOLVED),
        _rec("C_skill", "t1", policy.RESOLVED),
        _rec("C_skill", "t2", policy.RESOLVED),
    ]


def test_condition_stats_rates():
    stats = condition_stats(_matrix())
    assert stats["A_baseline"].resolved_rate == 0.0
    assert stats["B_prompt_instructions"].resolved_rate == 0.5
    assert stats["C_skill"].resolved_rate == 1.0
    assert stats["C_skill"].tasks == 2


def test_paired_effects():
    eff_c = paired_effect(_matrix(), "C_skill", "A_baseline")
    assert eff_c is not None and abs(eff_c.diff - 1.0) < 1e-9
    eff_b = paired_effect(_matrix(), "B_prompt_instructions", "A_baseline")
    assert eff_b is not None and abs(eff_b.diff - 0.5) < 1e-9


def test_infrastructure_errors_excluded_from_denominator():
    recs = [
        _rec("A_baseline", "t1", policy.RESOLVED),
        _rec("A_baseline", "t2", policy.INFRASTRUCTURE_ERROR),
    ]
    st = condition_stats(recs)["A_baseline"]
    assert st.counted == 1
    assert st.resolved_rate == 1.0
    assert st.infrastructure_errors == 1


def test_analyze_document_and_render():
    summary = analyze(_matrix(), n_resamples=300)
    assert summary["reference"] == "A_baseline"
    assert len(summary["effects"]) == 2
    text = render_text(summary)
    assert "C_skill" in text and "paired effects" in text
