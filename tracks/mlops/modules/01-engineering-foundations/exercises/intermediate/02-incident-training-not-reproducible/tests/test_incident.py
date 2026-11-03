import os
import random

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
PARTS = 4


@pytest.fixture(scope="module")
def pipeline():
    return ex.module("pipeline.py")


@pytest.fixture
def data_dir(tmp_path):
    rng = np.random.default_rng(0)
    folder = tmp_path / "trips"
    folder.mkdir()
    for part in range(PARTS):
        distance = np.round(rng.gamma(2.0, 1.5, 400) + 0.3, 2)
        hour = rng.integers(0, 24, 400)
        minutes = 4 + 3.2 * distance + 2.0 * np.isin(hour, [17, 18]) + rng.normal(0, 2.0, 400)
        pd.DataFrame({"trip_distance": distance, "hour": hour, "duration_min": minutes}).to_csv(folder / f"part-{part}.csv", index=False)
    (folder / "_SUCCESS").write_text("", encoding="utf-8")
    return folder


class PermutedScandir:
    def __init__(self, iterator, permutation):
        entries = sorted(iterator, key=lambda entry: entry.name)
        self.entries = [entries[i] for i in permutation(len(entries))]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self.entries)

    def close(self):
        pass


def list_in_order(monkeypatch, permutation):
    real_listdir, real_scandir = os.listdir, os.scandir

    def listing(path="."):
        names = sorted(real_listdir(path))
        return [names[i] for i in permutation(len(names))]

    def scanning(path="."):
        with real_scandir(path) as iterator:
            return PermutedScandir(list(iterator), permutation)

    monkeypatch.setattr(os, "listdir", listing)
    monkeypatch.setattr(os, "scandir", scanning)


def test_two_runs_same_seed_give_the_same_mae(pipeline, data_dir):
    random.seed(1)
    np.random.seed(1)
    first = pipeline.train(data_dir, seed=0)
    random.seed(2)
    np.random.seed(2)
    second = pipeline.train(data_dir, seed=0)
    assert first == second, f"MAE lần 1 {first:.6f}, lần 2 {second:.6f}: còn nguồn ngẫu nhiên chưa nằm dưới seed"


def test_result_does_not_depend_on_directory_listing_order(pipeline, data_dir, monkeypatch):
    results = []
    for permutation in (lambda n: range(n), lambda n: reversed(range(n)), lambda n: [(i + 2) % n for i in range(n)]):
        list_in_order(monkeypatch, permutation)
        results.append(pipeline.train(data_dir, seed=0))
    assert len(set(results)) == 1, f"MAE đổi theo thứ tự liệt kê tệp: {results}"


def test_seed_still_controls_the_split(pipeline, data_dir):
    assert pipeline.train(data_dir, seed=0) != pipeline.train(data_dir, seed=1)


def test_train_leaves_global_random_state_alone(pipeline, data_dir):
    random.seed(5)
    np.random.seed(5)
    python_state, numpy_state = random.getstate(), np.random.get_state()
    pipeline.train(data_dir, seed=0)
    assert random.getstate() == python_state, "train() làm đổi random của Python"
    after = np.random.get_state()
    assert after[0] == numpy_state[0] and (after[1] == numpy_state[1]).all() and after[2:] == numpy_state[2:], (
        "train() làm đổi np.random toàn cục"
    )


def test_ignores_non_csv_files_and_still_learns(pipeline, data_dir):
    mae = pipeline.train(data_dir, seed=0)
    frame = pipeline.load_trips(data_dir)
    assert len(frame) == PARTS * 400
    baseline = float((frame["duration_min"] - frame["duration_min"].mean()).abs().mean())
    assert mae < 0.6 * baseline
