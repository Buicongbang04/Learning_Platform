import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import subprocess
import time

import pytest
from mlflow import MlflowClient

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)

LOCK = """schema: '2.0'
stages:
  prepare:
    cmd: python prepare.py
    deps:
    - path: data/raw/trips.parquet
      md5: 1111aaaa
    outs:
    - path: data/clean/trips.parquet
      md5: {md5}
      size: 1234
  split:
    cmd: python split.py
    outs:
    - path: data/split
      md5: 9f8e7d6c5b4a39281706f5e4d3c2b1a0.dir
"""


def git(repo, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, env=env).stdout


@pytest.fixture
def lineage():
    return ex.module("lineage.py")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "train.py").write_text("print('v1')\n")
    (root / "dvc.lock").write_text(LOCK.format(md5="c0ffee01"))
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def tracking(tmp_path):
    uri = mlopskit.mlflow_local(tmp_path)
    client = MlflowClient(uri)
    exp = client.search_experiments(filter_string="name LIKE 'mlops-ex-%'")[0]
    return uri, exp.experiment_id


def test_git_state_clean_then_dirty(lineage, repo):
    head = git(repo, "rev-parse", "HEAD").strip()
    assert lineage.git_state(repo) == {"commit": head, "dirty": False}
    (repo / "train.py").write_text("print('v2')\n")
    assert lineage.git_state(repo) == {"commit": head, "dirty": True}


def test_git_state_untracked_file_is_dirty(lineage, repo):
    (repo / "notes.txt").write_text("x")
    assert lineage.git_state(repo)["dirty"] is True


def test_data_version_from_lock(lineage, repo):
    assert lineage.data_version_from_lock(repo / "dvc.lock", "prepare") == "c0ffee01"
    assert lineage.data_version_from_lock(repo / "dvc.lock", "split").endswith(".dir")


def test_data_version_unknown_stage_names_stage(lineage, repo):
    with pytest.raises(ValueError, match="train"):
        lineage.data_version_from_lock(repo / "dvc.lock", "train")


def test_log_run_has_lineage_tags(lineage, repo, tracking):
    uri, exp_id = tracking
    run_id = lineage.log_run(uri, exp_id, {"max_depth": 6, "lr": 0.1}, {"mae": 212.5},
                             repo, repo / "dvc.lock", "prepare")
    run = MlflowClient(uri).get_run(run_id)
    assert run.info.status == "FINISHED"
    assert run.data.tags["git_commit"] == git(repo, "rev-parse", "HEAD").strip()
    assert run.data.tags["git_dirty"] == "false"
    assert run.data.tags["data_version"] == "c0ffee01"
    assert run.data.params == {"max_depth": "6", "lr": "0.1"}
    assert run.data.metrics["mae"] == pytest.approx(212.5)


def test_log_run_marks_dirty_tree(lineage, repo, tracking):
    uri, exp_id = tracking
    (repo / "train.py").write_text("print('hack')\n")
    run_id = lineage.log_run(uri, exp_id, {}, {"mae": 1.0}, repo, repo / "dvc.lock", "prepare")
    assert MlflowClient(uri).get_run(run_id).data.tags["git_dirty"] == "true"


def test_log_run_does_not_change_global_tracking_uri(lineage, repo, tracking, tmp_path):
    import mlflow

    uri, exp_id = tracking
    before = mlflow.get_tracking_uri()
    other = f"sqlite:///{tmp_path / 'other.db'}"
    other_exp = MlflowClient(other).create_experiment("other", artifact_location=(tmp_path / "oa").as_uri())
    lineage.log_run(other, other_exp, {}, {"mae": 1.0}, repo, repo / "dvc.lock", "prepare")
    assert mlflow.get_tracking_uri() == before
    assert MlflowClient(uri).search_runs([exp_id]) == []


def test_find_runs_by_data_version_and_commit(lineage, repo, tracking):
    uri, exp_id = tracking
    lock = repo / "dvc.lock"
    first = lineage.log_run(uri, exp_id, {}, {"mae": 3.0}, repo, lock, "prepare")
    time.sleep(0.01)
    second = lineage.log_run(uri, exp_id, {}, {"mae": 2.0}, repo, lock, "prepare")
    first_commit = git(repo, "rev-parse", "HEAD").strip()

    (repo / "dvc.lock").write_text(LOCK.format(md5="deadbeef"))
    git(repo, "commit", "-qam", "new data")
    third = lineage.log_run(uri, exp_id, {}, {"mae": 1.0}, repo, lock, "prepare")

    assert lineage.find_runs(uri, exp_id, data_version="c0ffee01") == [second, first]
    assert lineage.find_runs(uri, exp_id, data_version="deadbeef") == [third]
    assert lineage.find_runs(uri, exp_id, git_commit=first_commit) == [second, first]
    assert lineage.find_runs(uri, exp_id, data_version="deadbeef", git_commit=first_commit) == []
    assert lineage.find_runs(uri, exp_id) == [third, second, first]


def test_find_runs_ignores_failed(lineage, repo, tracking):
    uri, exp_id = tracking
    client = MlflowClient(uri)
    bad = client.create_run(exp_id, tags={"data_version": "c0ffee01"})
    client.set_terminated(bad.info.run_id, status="FAILED")
    ok = lineage.log_run(uri, exp_id, {}, {"mae": 1.0}, repo, repo / "dvc.lock", "prepare")
    assert lineage.find_runs(uri, exp_id, data_version="c0ffee01") == [ok]
