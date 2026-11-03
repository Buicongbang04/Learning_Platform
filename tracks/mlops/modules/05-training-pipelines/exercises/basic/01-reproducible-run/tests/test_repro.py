import hashlib
import platform

import numpy as np
import pandas as pd
import pytest
import sklearn

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def mod():
    return ex.module("repro.py")


@pytest.fixture
def df(mod):
    return mod.make_dataset(300, seed=7)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fingerprint_is_stable_for_same_content(mod, df):
    assert mod.data_fingerprint(df) == mod.data_fingerprint(df.copy())
    assert len(mod.data_fingerprint(df)) == 64


def test_fingerprint_changes_when_one_cell_changes(mod, df):
    other = df.copy()
    other.loc[10, "duration_s"] += 1.0
    assert mod.data_fingerprint(other) != mod.data_fingerprint(df)


def test_fingerprint_depends_on_row_order(mod, df):
    assert mod.data_fingerprint(df.iloc[::-1].reset_index(drop=True)) != mod.data_fingerprint(df)


def test_same_seed_gives_byte_identical_artifact(mod, df, tmp_path):
    first = mod.save_artifact(mod.train(df, seed=3), tmp_path / "a.joblib")
    second = mod.save_artifact(mod.train(df, seed=3), tmp_path / "b.joblib")
    assert first == second


def test_different_seed_gives_different_artifact(mod, df, tmp_path):
    first = mod.save_artifact(mod.train(df, seed=3), tmp_path / "a.joblib")
    second = mod.save_artifact(mod.train(df, seed=4), tmp_path / "b.joblib")
    assert first != second


def test_result_does_not_depend_on_global_random_state(mod, df, tmp_path):
    np.random.seed(1)
    first = mod.save_artifact(mod.train(df, seed=3), tmp_path / "a.joblib")
    np.random.seed(2)
    second = mod.save_artifact(mod.train(df, seed=3), tmp_path / "b.joblib")
    assert first == second


def test_train_does_not_mutate_input(mod, df):
    before = df.copy(deep=True)
    mod.train(df, seed=0)
    pd.testing.assert_frame_equal(df, before)


def test_save_artifact_returns_sha256_of_file_bytes(mod, df, tmp_path):
    path = tmp_path / "m.joblib"
    assert mod.save_artifact(mod.train(df, seed=0), path) == sha(path)


def test_params_override_defaults(mod, df):
    model = mod.train(df, seed=0, params={"n_estimators": 5})
    assert model.n_estimators == 5
    assert model.max_depth == mod.DEFAULT_PARAMS["max_depth"]


def test_manifest_records_everything_needed_to_rerun(mod, df, tmp_path):
    path = tmp_path / "m.joblib"
    mod.save_artifact(mod.train(df, seed=3, params={"n_estimators": 5}), path)
    manifest = mod.build_manifest(df, 3, {"n_estimators": 5}, path)
    assert manifest["data_sha256"] == mod.data_fingerprint(df)
    assert manifest["seed"] == 3
    assert manifest["params"] == {**mod.DEFAULT_PARAMS, "n_estimators": 5}
    assert manifest["artifact_sha256"] == sha(path)
    assert manifest["python"] == platform.python_version()
    assert manifest["sklearn"] == sklearn.__version__
    assert manifest["numpy"] == np.__version__


def test_verify_accepts_untouched_and_rejects_tampered_or_missing(mod, df, tmp_path):
    path = tmp_path / "m.joblib"
    mod.save_artifact(mod.train(df, seed=3), path)
    manifest = mod.build_manifest(df, 3, None, path)
    assert mod.verify(manifest, path) is True
    path.write_bytes(path.read_bytes() + b"\0")
    assert mod.verify(manifest, path) is False
    assert mod.verify(manifest, tmp_path / "missing.joblib") is False


def test_rerun_from_manifest_reproduces_artifact_hash(mod, df, tmp_path):
    path = tmp_path / "m.joblib"
    mod.save_artifact(mod.train(df, seed=5, params={"max_depth": 4}), path)
    manifest = mod.build_manifest(df, 5, {"max_depth": 4}, path)
    again = tmp_path / "again.joblib"
    mod.save_artifact(mod.train(df, seed=manifest["seed"], params=manifest["params"]), again)
    assert mod.verify(manifest, again) is True
