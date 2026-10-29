import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import pytest
from mlflow import MlflowClient

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def tracking():
    return ex.module("tracking.py")


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    root = tmp_path_factory.mktemp("mlflow")
    return f"sqlite:///{root / 'mlflow.db'}", root / "artifacts"


def test_experiment_created_once_with_explicit_artifact_root(tracking, store):
    uri, artifacts = store
    first = tracking.get_or_create_experiment(uri, "bad-review", artifacts)
    second = tracking.get_or_create_experiment(uri, "bad-review", artifacts)
    assert first == second
    exp = MlflowClient(uri).get_experiment(first)
    assert exp.name == "bad-review"
    assert str(artifacts) in exp.artifact_location


def test_log_run_params_metrics_tags(tracking, store):
    uri, artifacts = store
    exp_id = tracking.get_or_create_experiment(uri, "log-test", artifacts)
    run_id = tracking.log_training_run(
        uri, exp_id,
        params={"model": "logreg", "C": 0.1, "features": 12},
        metrics={"val_auc": 0.7987, "val_logloss": 0.36},
        tags={"data_version": "olist-2018-08-31", "author": "ds"},
    )
    run = MlflowClient(uri).get_run(run_id)
    assert run.info.experiment_id == exp_id
    assert run.info.status == "FINISHED"
    assert run.data.params == {"model": "logreg", "C": "0.1", "features": "12"}
    assert run.data.metrics["val_auc"] == pytest.approx(0.7987)
    assert run.data.tags["data_version"] == "olist-2018-08-31"


def test_metric_list_is_logged_as_steps(tracking, store):
    uri, artifacts = store
    exp_id = tracking.get_or_create_experiment(uri, "steps", artifacts)
    curve = [0.70, 0.74, 0.76, 0.75]
    run_id = tracking.log_training_run(uri, exp_id, params={}, metrics={"val_auc": curve})
    history = MlflowClient(uri).get_metric_history(run_id, "val_auc")
    assert [m.step for m in sorted(history, key=lambda m: m.step)] == [0, 1, 2, 3]
    assert [m.value for m in sorted(history, key=lambda m: m.step)] == pytest.approx(curve)


def test_best_run_max_and_min(tracking, store):
    uri, artifacts = store
    exp_id = tracking.get_or_create_experiment(uri, "search", artifacts)
    ids = {}
    for C, auc, loss in [(0.01, 0.7998, 0.351), (1.0, 0.7987, 0.349), (10.0, 0.7983, 0.360)]:
        ids[C] = tracking.log_training_run(uri, exp_id, params={"C": C},
                                           metrics={"val_auc": auc, "val_logloss": loss})
    best = tracking.best_run(uri, exp_id, "val_auc")
    assert best["run_id"] == ids[0.01]
    assert best["params"] == {"C": "0.01"}
    assert best["value"] == pytest.approx(0.7998)
    assert tracking.best_run(uri, exp_id, "val_logloss", higher_is_better=False)["run_id"] == ids[1.0]


def test_best_run_ignores_failed_and_runs_without_metric(tracking, store):
    uri, artifacts = store
    exp_id = tracking.get_or_create_experiment(uri, "failed", artifacts)
    good = tracking.log_training_run(uri, exp_id, params={"C": 1}, metrics={"val_auc": 0.70})
    tracking.log_training_run(uri, exp_id, params={"C": 2}, metrics={"train_auc": 0.99})
    client = MlflowClient(uri)
    crashed = client.create_run(exp_id)
    client.log_metric(crashed.info.run_id, "val_auc", 0.95)       # run lỗi giữa chừng, metric không đáng tin
    client.set_terminated(crashed.info.run_id, status="FAILED")
    assert tracking.best_run(uri, exp_id, "val_auc")["run_id"] == good


def test_best_run_empty_experiment_raises(tracking, store):
    uri, artifacts = store
    exp_id = tracking.get_or_create_experiment(uri, "empty", artifacts)
    with pytest.raises(ValueError):
        tracking.best_run(uri, exp_id, "val_auc")


def test_nothing_written_to_working_directory(tracking, tmp_path, monkeypatch):
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    uri = f"sqlite:///{tmp_path / 'other.db'}"
    exp_id = tracking.get_or_create_experiment(uri, "cwd-check", tmp_path / "art")
    tracking.log_training_run(uri, exp_id, params={"C": 1}, metrics={"val_auc": 0.7})
    assert list(workdir.iterdir()) == []      # không có mlruns/ hay mlartifacts/ rơi vào thư mục làm việc
