import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import pytest
from mlflow import MlflowClient

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)

GOOD = {
    "git_commit": "a" * 40,
    "git_dirty": "false",
    "data_version": "c0ffee01d4",
    "lockfile_sha256": "b" * 64,
}

CASES = [
    ("full", {}, "42", []),
    ("negative-seed-is-int", {}, "-1", []),
    ("no-commit", {"git_commit": None}, "42", ["commit"]),
    ("short-commit", {"git_commit": "a" * 7}, "42", ["commit"]),
    ("uppercase-commit", {"git_commit": "A" * 40}, "42", ["commit"]),
    ("dirty-tree", {"git_dirty": "true"}, "42", ["commit"]),
    ("no-dirty-tag", {"git_dirty": None}, "42", ["commit"]),
    ("no-data", {"data_version": None}, "42", ["data_version"]),
    ("data-latest", {"data_version": "Latest"}, "42", ["data_version"]),
    ("data-unknown", {"data_version": "unknown"}, "42", ["data_version"]),
    ("data-blank", {"data_version": "  "}, "42", ["data_version"]),
    ("no-lock", {"lockfile_sha256": None}, "42", ["lockfile_hash"]),
    ("short-lock", {"lockfile_sha256": "b" * 40}, "42", ["lockfile_hash"]),
    ("lock-with-space", {"lockfile_sha256": "b" * 63 + " "}, "42", ["lockfile_hash"]),
    ("no-seed", {}, None, ["seed"]),
    ("seed-random", {}, "random", ["seed"]),
    ("seed-none", {}, "None", ["seed"]),
    ("two-missing", {"data_version": None, "lockfile_sha256": None}, "42", ["data_version", "lockfile_hash"]),
    ("all-missing", {k: None for k in GOOD}, None, ["commit", "data_version", "lockfile_hash", "seed"]),
]


@pytest.fixture
def audit():
    return ex.module("audit.py")


@pytest.fixture
def env(tmp_path):
    uri = mlopskit.mlflow_local(tmp_path)
    client = MlflowClient(uri)
    exp = client.search_experiments(filter_string="name LIKE 'mlops-ex-%'")[0]

    def make(overrides=None, seed="42"):
        tags = {**GOOD, **(overrides or {})}
        tags = {k: v for k, v in tags.items() if v is not None}
        run = client.create_run(exp.experiment_id, tags=tags)
        if seed is not None:
            client.log_param(run.info.run_id, "seed", seed)
        client.set_terminated(run.info.run_id, status="FINISHED")
        return run.info.run_id

    return uri, client, make


@pytest.mark.parametrize("name,overrides,seed,expected", CASES, ids=[c[0] for c in CASES])
def test_audit_run_table(audit, env, name, overrides, seed, expected):
    uri, _, make = env
    assert audit.audit_run(uri, make(overrides, seed)) == expected


def test_audit_is_read_only(audit, env):
    uri, client, make = env
    run_id = make({"git_commit": None})
    before = client.get_run(run_id)
    audit.audit_run(uri, run_id)
    after = client.get_run(run_id)
    assert after.data.tags == before.data.tags and after.data.params == before.data.params
    assert after.info.status == before.info.status


def register(client, name, run_id):
    client.create_registered_model(name)
    return int(client.create_model_version(name, source="file:///unused", run_id=run_id).version)


def test_audit_model_follows_the_version_not_the_latest_run(audit, env):
    uri, client, make = env
    old = make({"lockfile_sha256": None})
    version = register(client, "taxi-eta", old)
    make()
    result = audit.audit_model(uri, "taxi-eta", version)
    assert result == {"run_id": old, "missing": ["lockfile_hash"], "reproducible": False}


def test_audit_model_reproducible_when_complete(audit, env):
    uri, client, make = env
    run_id = make()
    version = register(client, "taxi-eta", run_id)
    assert audit.audit_model(uri, "taxi-eta", version) == {"run_id": run_id, "missing": [], "reproducible": True}


def test_run_of_version_unknown_names_model_and_version(audit, env):
    uri, client, make = env
    register(client, "taxi-eta", make())
    with pytest.raises(LookupError, match=r"taxi-eta.*9|9.*taxi-eta"):
        audit.run_of_version(uri, "taxi-eta", 9)
    with pytest.raises(LookupError, match="ghost"):
        audit.run_of_version(uri, "ghost", 1)
