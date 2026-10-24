"""Image-lock verification. Pure logic; no Docker required."""

from __future__ import annotations

from skills_experiment.locks import ImageLock, load_lock, save_lock, verify


def _lock(images: dict) -> ImageLock:
    return ImageLock(experiment_id="pilot-01", dataset_revision="sha", images=images)


def test_verify_ok_when_digests_match():
    lock = _lock({"a-1": {"image": "img:latest", "digest": "sha256:aaa"}})
    assert verify(lock, {"a-1": "sha256:aaa"}) == []


def test_verify_flags_digest_mismatch():
    lock = _lock({"a-1": {"image": "img:latest", "digest": "sha256:aaa"}})
    problems = verify(lock, {"a-1": "sha256:bbb"})
    assert len(problems) == 1
    assert "mismatch" in problems[0]


def test_verify_flags_missing_image():
    lock = _lock({"a-1": {"image": "img:latest", "digest": "sha256:aaa"}})
    problems = verify(lock, {"a-1": ""})
    assert problems
    assert "not present" in problems[0]


def test_verify_flags_stale_lock():
    lock = _lock({"a-1": {"image": "img:latest", "digest": "sha256:aaa"}})
    problems = verify(lock, {"a-1": "sha256:aaa", "b-2": "sha256:ccc"})
    assert any("not covered" in p for p in problems)


def test_save_load_roundtrip(tmp_path):
    lock = _lock({"a-1": {"image": "img:latest", "digest": "sha256:aaa"}})
    path = save_lock(lock, data_dir=tmp_path)
    assert path.exists()

    again = load_lock("pilot-01", data_dir=tmp_path)
    assert again is not None
    assert again.images == lock.images
    assert again.dataset_revision == "sha"
    assert again.created_at  # stamped on save


def test_load_missing_returns_none(tmp_path):
    assert load_lock("nope", data_dir=tmp_path) is None


def test_runner_enforces_image_lock(tmp_path, fake_task, monkeypatch):
    """A moved digest must abort the run; a matching one must pass."""
    import pytest

    from skills_experiment import locks
    from skills_experiment.config import load_experiment
    from skills_experiment.runner import ExperimentRunner
    from skills_experiment.sandbox import docker as docker_mod

    config = load_experiment("pilot")
    config.sandbox.kind = "docker"
    runner = ExperimentRunner(config, base_dir=tmp_path / "runs")
    tasks = [{"task": fake_task, "topic": "", "why": ""}]

    monkeypatch.setattr(
        locks,
        "load_lock",
        lambda *a, **k: locks.ImageLock(
            experiment_id=config.id,
            images={fake_task.instance_id: {"image": "img", "digest": "sha256:locked"}},
        ),
    )

    monkeypatch.setattr(docker_mod, "image_digest", lambda image: "sha256:different")
    with pytest.raises(locks.ImageLockError):
        runner._verify_image_lock(tasks)

    monkeypatch.setattr(docker_mod, "image_digest", lambda image: "sha256:locked")
    runner._verify_image_lock(tasks)  # no raise


def _fake_docker(monkeypatch, outputs):
    """Patch docker.subprocess/time; return the fake subprocess for call counts."""
    from skills_experiment.sandbox import docker as docker_mod

    class _Proc:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    class _FakeSubprocess:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, *args, **kwargs):
            self.calls += 1
            return _Proc(outputs[min(self.calls - 1, len(outputs) - 1)])

    class _FakeTime:
        @staticmethod
        def sleep(_seconds: float) -> None:
            return None

    fake = _FakeSubprocess()
    monkeypatch.setattr(docker_mod, "subprocess", fake)
    monkeypatch.setattr(docker_mod, "time", _FakeTime)
    return fake


def test_image_digest_retries_transient_empty(monkeypatch):
    """Docker can briefly report an image as absent while indexing it."""
    from skills_experiment.sandbox import docker as docker_mod

    fake = _fake_docker(monkeypatch, ["", "", "sha256:ok\n"])
    assert docker_mod.image_digest("img:latest") == "sha256:ok"
    assert fake.calls == 3


def test_image_digest_gives_up_after_retries(monkeypatch):
    """A genuinely missing image still resolves to '' (lock stays fail-closed)."""
    from skills_experiment.sandbox import docker as docker_mod

    fake = _fake_docker(monkeypatch, [""])
    assert docker_mod.image_digest("img:latest") == ""
    assert fake.calls == 3


def test_runner_lock_allows_partial_run(tmp_path, fake_task, monkeypatch):
    """A `--limit` subset must not be flagged for lock entries it won't use."""
    from skills_experiment import locks
    from skills_experiment.config import load_experiment
    from skills_experiment.runner import ExperimentRunner
    from skills_experiment.sandbox import docker as docker_mod

    config = load_experiment("pilot")
    config.sandbox.kind = "docker"
    runner = ExperimentRunner(config, base_dir=tmp_path / "runs")

    monkeypatch.setattr(
        locks,
        "load_lock",
        lambda *a, **k: locks.ImageLock(
            experiment_id=config.id,
            images={
                fake_task.instance_id: {"image": "img", "digest": "sha256:locked"},
                "other__task-2": {"image": "img2", "digest": "sha256:other"},
            },
        ),
    )
    monkeypatch.setattr(docker_mod, "image_digest", lambda image: "sha256:locked")

    # Only fake_task is part of this limited run; the other lock entry is unused.
    runner._verify_image_lock([{"task": fake_task, "topic": "", "why": ""}])  # no raise

