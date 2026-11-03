import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from testkit import Exercise

ex = Exercise(__file__)
MONTHS = ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]


def write_month(data_dir, month, index):
    rng = np.random.default_rng(100 + index)
    n = 250 + 50 * index
    distance = rng.gamma(2.0, 2.5, n)
    pd.DataFrame({"distance_km": distance, "duration_s": 80 + (130 + 20 * index) * distance + rng.normal(0, 20 + 8 * index, n)}).to_csv(
        data_dir / f"trips-{month}.csv", index=False)


def expected(data_dir, month):
    df = pd.read_csv(data_dir / f"trips-{month}.csv")
    model = LinearRegression().fit(df[["distance_km"]], df["duration_s"])
    mae = float((df["duration_s"] - model.predict(df[["distance_km"]])).abs().mean())
    return {"month": month, "rows": len(df), "mean_duration": float(df["duration_s"].mean()), "mae": mae}


def read(results, month):
    return json.loads((results / f"{month}.json").read_text())


@pytest.fixture
def mod():
    module = ex.module("monthly.py")
    return module


@pytest.fixture
def lake(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for index, month in enumerate(MONTHS):
        write_month(data_dir, month, index)
    return data_dir, tmp_path / "results"


def assert_month(results, data_dir, month):
    got, want = read(results, month), expected(data_dir, month)
    assert got["month"] == month and got["rows"] == want["rows"]
    assert got["mean_duration"] == pytest.approx(want["mean_duration"])
    assert got["mae"] == pytest.approx(want["mae"])


def test_months_have_distinguishable_numbers(lake):
    data_dir, _ = lake
    maes = {round(expected(data_dir, m)["mae"], 3) for m in MONTHS}
    assert len(maes) == len(MONTHS)


def test_single_month_run_is_correct(mod, lake):
    data_dir, results = lake
    mod.run_months(["2026-08"], data_dir, results)
    assert_month(results, data_dir, "2026-08")
    assert [p.name for p in results.iterdir()] == ["2026-08.json"]


def test_each_month_of_a_multi_month_run_has_its_own_numbers(mod, lake):
    data_dir, results = lake
    mod.run_months(MONTHS, data_dir, results)
    for month in MONTHS:
        assert_month(results, data_dir, month)


def test_backfill_leaves_previously_correct_months_unchanged(mod, lake):
    data_dir, results = lake
    for month in ("2026-09", "2026-10"):
        mod.run_months([month], data_dir, results)
    before = {m: (results / f"{m}.json").read_bytes() for m in ("2026-09", "2026-10")}
    mod.run_months(["2026-07", "2026-08", "2026-09", "2026-10"], data_dir, results)
    for month, content in before.items():
        assert (results / f"{month}.json").read_bytes() == content
    assert_month(results, data_dir, "2026-07")
    assert_month(results, data_dir, "2026-08")


def test_months_outside_the_backfill_are_not_touched(mod, lake):
    data_dir, results = lake
    mod.run_months(["2026-06", "2026-10"], data_dir, results)
    snapshot = {m: (results / f"{m}.json").read_bytes() for m in ("2026-06", "2026-10")}
    mod.run_months(["2026-07", "2026-08"], data_dir, results)
    assert {m: (results / f"{m}.json").read_bytes() for m in snapshot} == snapshot
    assert sorted(p.stem for p in results.iterdir()) == ["2026-06", "2026-07", "2026-08", "2026-10"]


def test_order_of_months_does_not_change_results(mod, lake, tmp_path):
    data_dir, results = lake
    mod.run_months(MONTHS, data_dir, results)
    reverse = tmp_path / "reverse"
    mod.run_months(list(reversed(MONTHS)), data_dir, reverse)
    for month in MONTHS:
        assert (results / f"{month}.json").read_bytes() == (reverse / f"{month}.json").read_bytes()


def test_rerunning_the_same_backfill_is_idempotent(mod, lake):
    data_dir, results = lake
    mod.run_months(MONTHS[:3], data_dir, results)
    first = {p.name: p.read_bytes() for p in results.iterdir()}
    mod.run_months(MONTHS[:3], data_dir, results)
    assert {p.name: p.read_bytes() for p in results.iterdir()} == first


def test_corrected_source_data_updates_only_that_month(mod, lake):
    data_dir, results = lake
    mod.run_months(MONTHS, data_dir, results)
    other = {m: (results / f"{m}.json").read_bytes() for m in MONTHS if m != "2026-08"}
    write_month(data_dir, "2026-08", 9)
    mod.run_months(["2026-08"], data_dir, results)
    assert_month(results, data_dir, "2026-08")
    assert {m: (results / f"{m}.json").read_bytes() for m in other} == other
