import time

import pytest

from testkit import Exercise

ex = Exercise(__file__)
BATCHES = 20
KEYS = {"num_workers", "batches", "wait_s", "compute_s", "wait_fraction", "samples_per_s"}


@pytest.fixture(scope="module")
def mod():
    return ex.module("loader_bench.py")


def test_single_process_loading_is_the_bottleneck(mod):
    report = mod.profile(mod.SlowDataset(), 0, batches=BATCHES, warmup=3)
    assert set(report) == KEYS
    assert report["num_workers"] == 0 and report["batches"] == BATCHES
    assert report["wait_s"] >= 0.9 * BATCHES * mod.BATCH * mod.DECODE_S
    assert BATCHES * mod.STEP_S * 0.9 <= report["compute_s"] <= BATCHES * mod.STEP_S * 2.5
    total = report["wait_s"] + report["compute_s"]
    assert report["wait_fraction"] == pytest.approx(report["wait_s"] / total)
    assert report["samples_per_s"] == pytest.approx(BATCHES * mod.BATCH / total)
    assert report["wait_fraction"] > 0.4
    assert mod.diagnose(report) == "data"


def test_enough_workers_hide_loading(mod):
    slow = mod.profile(mod.SlowDataset(), 0, batches=BATCHES, warmup=3)
    fast = mod.profile(mod.SlowDataset(), 4, batches=BATCHES, warmup=5)
    assert fast["wait_fraction"] < 0.2
    assert mod.diagnose(fast) == "compute"
    assert fast["samples_per_s"] > 1.5 * slow["samples_per_s"]


def test_step_and_batch_size_are_respected(mod):
    sizes = []
    report = mod.profile(mod.SlowDataset(), 0, batches=6, warmup=2, batch_size=8, step=lambda b: sizes.append(len(b)))
    assert sizes == [8] * 8
    assert report["samples_per_s"] == pytest.approx(6 * 8 / (report["wait_s"] + report["compute_s"]))


def test_warmup_batches_are_not_counted(mod):
    calls = []

    def step(batch):
        calls.append(len(batch))
        time.sleep(0.3 if len(calls) <= 2 else 0.01)

    report = mod.profile(mod.SlowDataset(), 0, batches=6, warmup=2, step=step)
    assert len(calls) == 8
    assert report["compute_s"] < 0.3
    assert report["wait_s"] < 6 * mod.BATCH * mod.DECODE_S * 2.5


def test_slow_step_makes_compute_the_bottleneck(mod):
    report = mod.profile(mod.SlowDataset(), 0, batches=8, warmup=1, step=lambda b: time.sleep(0.2))
    assert report["compute_s"] >= 8 * 0.2
    assert mod.diagnose(report) == "compute"


def test_diagnose_threshold(mod):
    assert mod.diagnose({"wait_fraction": 0.5}) == "data"
    assert mod.diagnose({"wait_fraction": 0.1}) == "compute"
    assert mod.diagnose({"wait_fraction": 0.3}, threshold=0.4) == "compute"


def test_smallest_sufficient_workers(mod):
    chosen, reports = mod.smallest_sufficient(mod.SlowDataset(), candidates=(4, 0, 1, 2), batches=BATCHES)
    measured = [r["num_workers"] for r in reports]
    assert measured == sorted(measured) and measured[0] == 0
    assert chosen == measured[-1] and chosen in (2, 4)
    assert all(mod.diagnose(r) == "data" for r in reports[:-1])
    assert mod.diagnose(reports[-1]) == "compute"


def test_none_when_no_candidate_is_enough(mod):
    chosen, reports = mod.smallest_sufficient(mod.SlowDataset(), candidates=(0,), batches=5)
    assert chosen is None and len(reports) == 1
