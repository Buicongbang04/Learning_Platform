import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
MONTHS = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04"]


def write_month(data_dir, month, index):
    rng = np.random.default_rng(index)
    n = 200 + 40 * index
    distance = rng.gamma(2.0, 2.5, n)
    slope = 140 + 15 * index
    pd.DataFrame({"distance_km": distance, "duration_s": 90 + slope * distance + rng.normal(0, 25, n)}).to_csv(
        data_dir / f"trips-{month}.csv", index=False)


@pytest.fixture(scope="module")
def mod():
    return ex.module("backfill.py")


@pytest.fixture
def lake(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for index, month in enumerate(MONTHS):
        write_month(data_dir, month, index)
    return data_dir, tmp_path / "out"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_month_range_inclusive_and_crosses_year(mod):
    assert mod.month_range("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert mod.month_range("2026-03", "2026-03") == ["2026-03"]


def test_month_range_rejects_reversed_or_malformed(mod):
    with pytest.raises(ValueError):
        mod.month_range("2026-03", "2026-01")
    with pytest.raises(ValueError):
        mod.month_range("2026-3", "2026-04")
    with pytest.raises(ValueError):
        mod.month_range("2026-13", "2026-14")


def test_backfill_creates_one_artifact_and_metadata_per_month(mod, lake):
    data_dir, out = lake
    result = mod.backfill("2025-12", "2026-03", data_dir, out)
    assert result["done"] == ["2025-12", "2026-01", "2026-02", "2026-03"]
    assert result["failed"] == {}
    assert sorted(p.name for p in out.glob("model-*.joblib")) == [f"model-{m}.joblib" for m in result["done"]]
    assert sorted(p.name for p in out.glob("model-*.json")) == [f"model-{m}.json" for m in result["done"]]


def test_each_month_is_trained_on_its_own_data(mod, lake):
    data_dir, out = lake
    mod.backfill("2026-01", "2026-03", data_dir, out)
    seen = set()
    for month in ("2026-01", "2026-02", "2026-03"):
        meta = json.loads((out / f"model-{month}.json").read_text())
        source = data_dir / f"trips-{month}.csv"
        assert meta["month"] == month
        assert meta["rows"] == len(pd.read_csv(source))
        assert meta["data_sha256"] == sha(source)
        seen.add(meta["mae"])
    assert len(seen) == 3


def test_single_month_run_matches_the_same_month_inside_a_backfill(mod, lake, tmp_path):
    data_dir, out = lake
    mod.backfill("2025-12", "2026-02", data_dir, out)
    alone = tmp_path / "alone"
    mod.train_month("2026-01", data_dir, alone)
    assert json.loads((alone / "model-2026-01.json").read_text()) == json.loads((out / "model-2026-01.json").read_text())


def test_rerun_without_overwrite_keeps_existing_files_untouched(mod, lake):
    data_dir, out = lake
    mod.backfill("2026-01", "2026-02", data_dir, out)
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    result = mod.backfill("2026-01", "2026-03", data_dir, out)
    assert result["skipped"] == ["2026-01", "2026-02"]
    assert result["done"] == ["2026-03"]
    assert all((out / name).read_bytes() == data for name, data in before.items())


def test_overwrite_true_retrains_existing_months(mod, lake):
    data_dir, out = lake
    mod.backfill("2026-01", "2026-02", data_dir, out)
    stale = out / "model-2026-02.json"
    stale.write_text("{}")
    result = mod.backfill("2026-01", "2026-02", data_dir, out, overwrite=True)
    assert result["done"] == ["2026-01", "2026-02"]
    assert json.loads(stale.read_text())["month"] == "2026-02"


def test_missing_month_is_reported_and_does_not_stop_the_others(mod, lake):
    data_dir, out = lake
    (data_dir / "trips-2026-02.csv").unlink()
    result = mod.backfill("2026-01", "2026-03", data_dir, out)
    assert result["done"] == ["2026-01", "2026-03"]
    assert list(result["failed"]) == ["2026-02"]
    assert not (out / "model-2026-02.joblib").exists()
    assert not (out / "model-2026-02.json").exists()


def test_failed_month_leaves_no_partial_files_and_can_be_retried(mod, lake):
    data_dir, out = lake
    (data_dir / "trips-2026-02.csv").write_text("distance_km,duration_s\n")
    result = mod.backfill("2026-02", "2026-02", data_dir, out)
    assert list(result["failed"]) == ["2026-02"]
    assert list(out.glob("model-2026-02*")) == []
    write_month(data_dir, "2026-02", 3)
    assert mod.backfill("2026-02", "2026-02", data_dir, out)["done"] == ["2026-02"]


def test_artifact_loads_and_predicts(mod, lake):
    import joblib

    data_dir, out = lake
    mod.backfill("2026-04", "2026-04", data_dir, out)
    model = joblib.load(out / "model-2026-04.joblib")
    assert model.predict(pd.DataFrame({"distance_km": [3.0]})).shape == (1,)
