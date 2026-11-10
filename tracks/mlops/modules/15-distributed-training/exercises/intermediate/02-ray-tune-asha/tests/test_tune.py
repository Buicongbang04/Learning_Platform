import math
import signal

import distkit
import mlopskit
import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)
SAMPLES = 12
TUNE_TIMEOUT = 180
EXPIRED = {"hit": False}


class TuneTimeout(BaseException):
    pass


def expire(signum, frame):
    EXPIRED["hit"] = True
    raise TuneTimeout


@pytest.fixture(scope="module")
def outcome():
    mod = ex.module("tune_search.py")
    distkit.pickle_by_value(mod)
    with mlopskit.ray_local(num_cpus=2) as storage:
        previous = signal.signal(signal.SIGALRM, expire)
        signal.alarm(TUNE_TIMEOUT)
        try:
            grid = mod.search(str(storage), num_samples=SAMPLES)
            trials = [{"config": dict(r.config), "iterations": r.metrics.get("training_iteration"),
                       "loss": r.metrics.get("loss"), "error": r.error is not None} for r in grid]
            chosen = mod.best(grid)
            written = sorted(p.name for p in storage.iterdir())
        except (TuneTimeout, Exception) as error:
            if EXPIRED["hit"]:
                return {"failed": f"Tìm kiếm chưa xong sau {TUNE_TIMEOUT} giây (trial chờ tài nguyên mãi hoặc quá chậm)"}
            return {"failed": f"{type(error).__name__}: {error}"}
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
    return {"trials": trials, "best": chosen, "written": written}


def done(outcome):
    assert "failed" not in outcome, outcome.get("failed")
    return outcome


def test_all_trials_ran_without_error(outcome):
    trials = done(outcome)["trials"]
    assert len(trials) == SAMPLES
    assert not any(t["error"] for t in trials)
    assert all(t["loss"] is not None and math.isfinite(t["loss"]) for t in trials)


def test_results_stored_under_given_storage(outcome):
    assert done(outcome)["written"], "Không có gì được ghi vào storage_path"


def test_some_trials_were_stopped_early(outcome):
    trials = done(outcome)["trials"]
    max_epochs = ex.module("tune_search.py").MAX_EPOCHS
    iterations = [t["iterations"] for t in trials]
    assert max(iterations) == max_epochs
    assert sum(1 for i in iterations if i < max_epochs) > 0


def test_configs_cover_the_search_space(outcome):
    mod = ex.module("tune_search.py")
    trials = done(outcome)["trials"]
    low, high = mod.LR_RANGE
    for t in trials:
        assert set(t["config"]) == {"lr", "hidden"}
        assert low <= t["config"]["lr"] <= high
        assert t["config"]["hidden"] in mod.HIDDEN_CHOICES
    assert len({t["config"]["lr"] for t in trials}) == SAMPLES


def test_best_is_the_lowest_final_loss(outcome):
    result = done(outcome)
    lowest = min(result["trials"], key=lambda t: t["loss"])
    assert result["best"]["loss"] == pytest.approx(lowest["loss"])
    assert result["best"]["config"] == lowest["config"]


def test_best_config_really_learns(outcome):
    mod = ex.module("tune_search.py")
    _, _, _, y_val = mod.make_data()
    baseline = torch.mean((y_val - y_val.mean()) ** 2).item()
    assert done(outcome)["best"]["loss"] < 0.5 * baseline
