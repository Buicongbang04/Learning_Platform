import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow import MlflowClient
from prefect.tasks import Task

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)
NAME = "taxi-eta"


def make_df(n=400, seed=0):
    rng = np.random.default_rng(seed)
    distance = rng.gamma(2.0, 2.5, n)
    hour = rng.integers(0, 24, n)
    return pd.DataFrame({"distance_km": distance, "hour": hour, "duration_s": 120 + 170 * distance + rng.normal(0, 30, n)})


class Loader:
    def __init__(self, fail_times=0, error=ConnectionError):
        self.fail_times = fail_times
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.error("tạm thời")
        return make_df()


@pytest.fixture(scope="module")
def mod():
    return ex.module("pipeline.py")


@pytest.fixture
def uri(tmp_path):
    return mlopskit.mlflow_local(tmp_path)


def test_stages_are_prefect_tasks_and_flow(mod):
    for name in ("read_data", "train_model", "evaluate_model", "register_model"):
        assert isinstance(getattr(mod, name), Task), name
    assert hasattr(mod.training_flow, "fn")


def test_retry_delay_is_short_enough_for_tests(mod):
    delay = mod.read_data.retry_delay_seconds
    assert delay is not None and max(delay if isinstance(delay, list) else [delay]) <= 1


def test_clean_run_reads_once_and_registers_version_one(mod, uri):
    loader = Loader()
    result = mod.training_flow(loader, uri, model_name=NAME)
    assert loader.calls == 1
    assert result["version"] == 1
    assert result["r2"] > 0.9
    assert [int(v.version) for v in MlflowClient(uri).search_model_versions(f"name='{NAME}'")] == [1]


def test_two_transient_failures_are_retried_and_flow_completes(mod, uri):
    loader = Loader(fail_times=2)
    result = mod.training_flow(loader, uri, model_name=NAME)
    assert loader.calls == 3
    assert result["version"] == 1


def test_three_transient_failures_exhaust_retries_and_nothing_is_registered(mod, uri):
    loader = Loader(fail_times=3)
    with pytest.raises(ConnectionError):
        mod.training_flow(loader, uri, model_name=NAME)
    assert loader.calls == 3
    assert MlflowClient(uri).search_registered_models() == []


def test_timeout_error_counts_as_transient(mod, uri):
    loader = Loader(fail_times=1, error=TimeoutError)
    assert mod.training_flow(loader, uri, model_name=NAME)["version"] == 1
    assert loader.calls == 2


def test_permanent_error_is_not_retried(mod, uri):
    loader = Loader(fail_times=5, error=ValueError)
    with pytest.raises(ValueError):
        mod.training_flow(loader, uri, model_name=NAME)
    assert loader.calls == 1


def test_model_below_quality_gate_is_not_registered(mod, uri):
    result = mod.training_flow(Loader(), uri, model_name=NAME, min_r2=0.9999)
    assert result["version"] is None
    assert result["r2"] < 0.9999
    assert MlflowClient(uri).search_registered_models() == []


def test_registered_version_links_to_run_with_metric_and_seed(mod, uri):
    mod.training_flow(Loader(), uri, model_name=NAME, seed=11)
    client = MlflowClient(uri)
    version = client.get_model_version(NAME, "1")
    run = client.get_run(version.run_id)
    assert run.data.params["seed"] == "11"
    assert run.data.metrics["r2"] > 0.9


def test_second_run_creates_version_two(mod, uri):
    mod.training_flow(Loader(), uri, model_name=NAME)
    assert mod.training_flow(Loader(), uri, model_name=NAME)["version"] == 2


def test_same_seed_gives_same_r2(mod, uri):
    first = mod.training_flow(Loader(), uri, model_name=NAME, seed=4)["r2"]
    assert mod.training_flow(Loader(), uri, model_name=NAME, seed=4)["r2"] == pytest.approx(first)
