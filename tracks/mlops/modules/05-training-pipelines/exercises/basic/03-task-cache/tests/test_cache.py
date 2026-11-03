import itertools

import numpy as np
import pandas as pd
import pytest
from prefect.tasks import Task

from testkit import Exercise

ex = Exercise(__file__)
_fresh = itertools.count(1000)


def write_csv(path, seed, n=300):
    rng = np.random.default_rng(seed)
    distance = rng.gamma(2.0, 2.5, n)
    hour = rng.integers(0, 24, n)
    pd.DataFrame({"distance_km": distance, "hour": hour, "duration_s": 100 + 160 * distance + rng.normal(0, 30, n)}).to_csv(path, index=False)


@pytest.fixture(scope="module")
def mod():
    return ex.module("cached.py")


@pytest.fixture
def data(tmp_path):
    path = tmp_path / "trips.csv"
    write_csv(path, seed=next(_fresh))
    return path


@pytest.fixture
def calls(mod):
    mod.CALLS.clear()
    return mod.CALLS


def need_cache(mod):
    assert getattr(mod.fit, "cache_key_fn", None) is not None, "Task fit chưa đặt cache_key_fn"


def test_fit_is_a_prefect_task_with_cache_key_fn(mod):
    assert isinstance(mod.fit, Task)
    assert mod.fit.cache_key_fn is mod.data_cache_key


def test_cache_key_is_equal_for_same_file_and_params(mod, data):
    params = {"data_path": str(data), "n_estimators": 10, "seed": 0}
    assert mod.data_cache_key(None, params) == mod.data_cache_key(None, dict(params))


def test_cache_key_changes_with_params(mod, data):
    base = {"data_path": str(data), "n_estimators": 10, "seed": 0}
    keys = {mod.data_cache_key(None, base)}
    keys.add(mod.data_cache_key(None, {**base, "n_estimators": 11}))
    keys.add(mod.data_cache_key(None, {**base, "seed": 1}))
    assert len(keys) == 3


def test_cache_key_changes_when_file_content_changes_at_same_path(mod, data):
    params = {"data_path": str(data), "n_estimators": 10, "seed": 0}
    before = mod.data_cache_key(None, params)
    write_csv(data, seed=next(_fresh))
    assert mod.data_cache_key(None, params) != before


def test_cache_key_ignores_file_location_and_mtime(mod, data, tmp_path):
    params = {"data_path": str(data), "n_estimators": 10, "seed": 0}
    before = mod.data_cache_key(None, params)
    data.touch()
    assert mod.data_cache_key(None, params) == before
    copy = tmp_path / "copy.csv"
    copy.write_bytes(data.read_bytes())
    assert mod.data_cache_key(None, {**params, "data_path": str(copy)}) == before


def test_same_parameters_do_not_train_again(mod, data, calls):
    need_cache(mod)
    first = mod.train_flow(str(data), n_estimators=8, seed=0)
    second = mod.train_flow(str(data), n_estimators=8, seed=0)
    assert len(calls) == 1
    assert first == second


def test_different_parameters_train_again(mod, data, calls):
    need_cache(mod)
    mod.train_flow(str(data), n_estimators=8, seed=0)
    mod.train_flow(str(data), n_estimators=9, seed=0)
    mod.train_flow(str(data), n_estimators=8, seed=1)
    assert len(calls) == 3


def test_changed_data_at_same_path_trains_again(mod, data, calls):
    need_cache(mod)
    mod.train_flow(str(data), n_estimators=8, seed=0)
    write_csv(data, seed=next(_fresh))
    mod.train_flow(str(data), n_estimators=8, seed=0)
    assert len(calls) == 2


def test_result_is_small_json_with_metrics(mod, data, calls):
    need_cache(mod)
    result = mod.train_flow(str(data), n_estimators=8, seed=0)
    assert set(result) == {"r2", "rows", "n_estimators", "seed"}
    assert result["rows"] == 300
    assert result["r2"] > 0.8


def test_cache_hit_returns_identical_metrics_not_a_new_fit(mod, data, calls):
    need_cache(mod)
    first = mod.train_flow(str(data), n_estimators=8, seed=2)
    second = mod.train_flow(str(data), n_estimators=8, seed=2)
    assert first["r2"] == second["r2"]
    assert len(calls) == 1
