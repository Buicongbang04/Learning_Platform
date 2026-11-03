import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

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
        import json

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


def test_replay_matches_original_with_a_different_index(env):
    _, train, replay, original = env
    run_id = train(index_of("1.4.0"))
    later = index_of("1.4.0", "1.5.0", "1.6.0")
    assert replay(run_id, later) == pytest.approx(original(run_id), abs=1e-9)


def test_fixture_sanity_two_indexes_give_different_models(env):
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
