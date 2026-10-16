"""Failure-handling policy + grading orchestration (no Docker required)."""

from __future__ import annotations

from skills_experiment.config import ExperimentConfig
from skills_experiment.evaluation import grade as grade_mod
from skills_experiment.evaluation import policy
from skills_experiment.evaluation.harness import HarnessResult
from skills_experiment.runlog import RunLogger, RunRecord


def _result(**kwargs) -> HarnessResult:
    return HarnessResult(run_id="r", returncode=0, **kwargs)


def test_classify_resolved_and_unresolved():
    res = _result(resolved_ids=["i1"], unresolved_ids=["i2"])
    assert policy.classify_harness_result("patch", "i1", res).status == policy.RESOLVED
    c = policy.classify_harness_result("patch", "i2", res)
    assert c.status == policy.UNRESOLVED and c.category == "tests_failed"


def test_classify_empty_patch_is_agent_failure():
    res = _result(empty_patch_ids=["i1"], unresolved_ids=["i1"])
    c = policy.classify_harness_result("   ", "i1", res)
    assert c.status == policy.UNRESOLVED and c.category == "empty_patch"


def test_classify_infra_failure():
    res = _result(infra_failure_ids=["i1"], failure_reasons={"i1": "image pull failed"})
    c = policy.classify_harness_result("patch", "i1", res)
    assert c.status == policy.INFRASTRUCTURE_ERROR and c.category == "image pull failed"


def test_classify_error_patch_apply_is_unresolved():
    res = _result(error_ids=["i1"], failure_reasons={"i1": "could not apply patch"})
    c = policy.classify_harness_result("patch", "i1", res)
    assert c.status == policy.UNRESOLVED and c.category == "patch_apply_fail"


def test_classify_error_without_apply_is_infra():
    res = _result(error_ids=["i1"], failure_reasons={"i1": "timeout"})
    c = policy.classify_harness_result("patch", "i1", res)
    assert c.status == policy.INFRASTRUCTURE_ERROR


def test_classify_missing_is_infra():
    res = _result()
    c = policy.classify_harness_result("patch", "i1", res)
    assert c.status == policy.INFRASTRUCTURE_ERROR and c.category == "not_in_report"


def test_collect_test_stats_reads_per_instance_reports(tmp_path):
    import json

    from skills_experiment.evaluation.harness import collect_test_stats

    run_id = "study__A__a1"
    report_dir = tmp_path / "logs" / "run_evaluation" / run_id / "model" / "task-0"
    report_dir.mkdir(parents=True)
    (report_dir / "report.json").write_text(
        json.dumps(
            {
                "task-0": {
                    "tests_status": {
                        "FAIL_TO_PASS": {"success": ["t1"], "failure": []},
                        "PASS_TO_PASS": {"success": ["t2", "t3"], "failure": ["t4"]},
                        "FAIL_TO_FAIL": {"success": ["t5"], "failure": []},
                        "PASS_TO_FAIL": {"success": [], "failure": []},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    stats = collect_test_stats(tmp_path, run_id, ["task-0", "missing"])
    assert "missing" not in stats
    s = stats["task-0"]
    assert s["tests_passed"] == 4
    assert s["tests_total"] == 5
    assert s["fail_to_pass_passed"] == 1
    assert s["fail_to_pass_total"] == 1
    assert s["pass_to_pass_passed"] == 2
    assert s["pass_to_pass_total"] == 3


def test_should_rerun_respects_budget():
    assert policy.should_rerun(policy.INFRASTRUCTURE_ERROR, 0, 1) is True
    assert policy.should_rerun(policy.INFRASTRUCTURE_ERROR, 1, 1) is False
    assert policy.should_rerun(policy.RESOLVED, 0, 5) is False
    assert policy.should_rerun(policy.UNRESOLVED, 0, 5) is False


def _config() -> ExperimentConfig:
    return ExperimentConfig(id="grade-test", model="mock", conditions=["A_baseline"])


def _seed_log(base_dir, config):
    """Write three attempt rows, each with a non-empty patch file on disk."""
    logger = RunLogger(config.id, base_dir)
    records = []
    for i, cond in enumerate(["A_baseline", "B_prompt_instructions", "C_skill"]):
        rec = RunRecord(
            experiment_id=config.id,
            condition=cond,
            instance_id=f"task-{i}",
            attempt_number=1,
            run_order=i,
        )
        patch = logger.attempt_dir(rec.instance_id, cond, 1) / "patch.diff"
        patch.write_text("diff --git a/x b/x\n", encoding="utf-8")
        rec.patch_path = str(patch)
        logger.append(rec)
        records.append(rec)
    return logger


def test_grade_updates_log_in_place(tmp_path, monkeypatch):
    import json
    from pathlib import Path

    base_dir = tmp_path / "runs"
    config = _config()
    logger = _seed_log(base_dir, config)

    calls = []

    def fake_run_harness(**kwargs):
        calls.append(kwargs["run_id"])
        lines = Path(kwargs["predictions_path"]).read_text(encoding="utf-8").splitlines()
        ids = [json.loads(line)["instance_id"] for line in lines if line.strip()]
        # resolve the first instance, mark the rest unresolved
        return HarnessResult(
            run_id=kwargs["run_id"],
            returncode=0,
            resolved_ids=[ids[0]] if ids else [],
            unresolved_ids=list(ids[1:]),
        )

    monkeypatch.setattr(grade_mod, "harness_version", lambda py: "5.0.2")
    monkeypatch.setattr(grade_mod, "run_harness", fake_run_harness)

    summary = grade_mod.grade_experiment(config, base_dir=base_dir, only_missing=True)
    assert summary.groups == 3
    assert summary.graded_attempts == 3

    reloaded = logger.load_records()
    for rec in reloaded:
        assert rec.harness_version == "5.0.2"
        assert rec.evaluation_status in {policy.RESOLVED, policy.UNRESOLVED}
        assert rec.failure_category in {"", "tests_failed"}

    # re-grading the already-counted attempts is skipped
    monkeypatch.setattr(grade_mod, "run_harness", fake_run_harness)
    summary2 = grade_mod.grade_experiment(config, base_dir=base_dir, only_missing=True)
    assert summary2.graded_attempts == 0
