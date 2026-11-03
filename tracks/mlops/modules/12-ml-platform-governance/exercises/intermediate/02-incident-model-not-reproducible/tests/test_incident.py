import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import hashlib
import json
import re
from pathlib import Path

import pytest
from mlflow import MlflowClient

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
LIBS = Path(__file__).parent / "fixtures" / "libs"


def index_of(*versions):
    return {"scalekit": {v: LIBS / v for v in versions}}


@pytest.fixture
def pipe():
    return ex.module("pipeline.py")


@pytest.fixture
def env(tmp_path, pipe):
    uri = mlopskit.mlflow_local(tmp_path / "mlflow")
    client = MlflowClient(uri)
    exp = client.search_experiments(filter_string="name LIKE 'mlops-ex-%'")[0]

    def train(index, seed=7, alpha=1.0, name="train"):
        return pipe.train_and_log(uri, exp.experiment_id, tmp_path / name, index, seed=seed, alpha=alpha)

    def replay(run_id, index, name="replay"):
        return pipe.replay(uri, run_id, tmp_path / name, index)

    def original(run_id):
        path = client.download_artifacts(run_id, "preds.json", str(tmp_path / "dl"))
        return json.loads(Path(path).read_text(encoding="utf-8"))

    return client, train, replay, original


def test_run_logs_everything_the_audit_asks_for(env):
    client, train, _, _ = env
    run = client.get_run(train(index_of("1.4.0")))
    assert run.info.status == "FINISHED"
    tags = run.data.tags
    assert re.fullmatch(r"[0-9a-f]{40}", tags["git_commit"]) and tags["git_dirty"] == "false"
    assert tags["data_version"] and re.fullmatch(r"[0-9a-f]{64}", tags["lockfile_sha256"])
    assert run.data.params["seed"] == "7" and run.data.params["alpha"] == "1.0"


def test_replay_matches_original_when_nothing_changed(env):
    _, train, replay, original = env
    index = index_of("1.4.0")
    run_id = train(index)
    assert replay(run_id, index) == pytest.approx(original(run_id), abs=1e-9)


def test_replay_matches_original_in_a_later_environment(env):
    _, train, replay, original = env
    run_id = train(index_of("1.4.0"))
    later = index_of("1.4.0", "1.5.0", "1.6.0")
    assert replay(run_id, later) == pytest.approx(original(run_id), abs=1e-9)


def test_fixture_sanity_two_environments_differ(env):
    _, train, replay, original = env
    old = train(index_of("1.4.0"), name="old")
    new = train(index_of("1.4.0", "1.5.0"), name="new")
    assert max(abs(a - b) for a, b in zip(original(old), original(new))) > 1e-3


def test_replay_of_a_second_run_matches_original(env):
    _, train, replay, original = env
    run_id = train(index_of("1.4.0", "1.5.0"))
    assert replay(run_id, index_of("1.4.0", "1.5.0", "1.6.0")) == pytest.approx(original(run_id), abs=1e-9)


def test_replay_is_repeatable(env):
    _, train, replay, _ = env
    run_id = train(index_of("1.4.0"))
    later = index_of("1.4.0", "1.5.0")
    assert replay(run_id, later, name="r1") == replay(run_id, later, name="r2")


def test_replay_fails_loudly_when_it_cannot_rebuild(env):
    _, train, replay, _ = env
    run_id = train(index_of("1.4.0"))
    with pytest.raises(LookupError, match=r"scalekit.*1\.4\.0|1\.4\.0.*scalekit"):
        replay(run_id, index_of("1.5.0", "1.6.0"))


def test_replay_refuses_a_run_logged_before_the_fix(env, tmp_path):
    client, _, replay, _ = env
    exp = client.search_experiments(filter_string="name LIKE 'mlops-ex-%'")[0]
    tags = {"git_commit": "c" * 40, "git_dirty": "false", "data_version": "synthetic-t3-v1",
            "lockfile_sha256": hashlib.sha256(b"scalekit>=1.4\n").hexdigest()}
    run_id = client.create_run(exp.experiment_id, tags=tags).info.run_id
    client.log_param(run_id, "seed", "7")
    client.log_param(run_id, "alpha", "1.0")
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "requirements.txt").write_text("scalekit>=1.4\n", encoding="utf-8")
    (legacy / "preds.json").write_text(json.dumps([0.0] * 5), encoding="utf-8")
    client.log_artifact(run_id, str(legacy / "requirements.txt"))
    client.log_artifact(run_id, str(legacy / "preds.json"))
    client.set_terminated(run_id, status="FINISHED")
    with pytest.raises(LookupError):
        replay(run_id, index_of("1.4.0", "1.5.0", "1.6.0"))


def test_replay_does_not_modify_the_original_run(env):
    client, train, replay, _ = env
    run_id = train(index_of("1.4.0"))
    before = client.get_run(run_id)
    artifacts_before = sorted(a.path for a in client.list_artifacts(run_id))
    replay(run_id, index_of("1.4.0", "1.5.0"))
    after = client.get_run(run_id)
    assert (after.data.tags, after.data.params, after.data.metrics, after.info.status) == (
        before.data.tags, before.data.params, before.data.metrics, before.info.status)
    assert sorted(a.path for a in client.list_artifacts(run_id)) == artifacts_before


def test_failed_training_does_not_leave_a_running_run(env, pipe, monkeypatch):
    client, train, _, _ = env
    monkeypatch.setattr(pipe, "run_trainer", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hỏng")))
    with pytest.raises(RuntimeError):
        train(index_of("1.4.0"))
    runs = client.search_runs([e.experiment_id for e in client.search_experiments(filter_string="name LIKE 'mlops-ex-%'")])
    assert runs and all(r.info.status == "FAILED" for r in runs)
