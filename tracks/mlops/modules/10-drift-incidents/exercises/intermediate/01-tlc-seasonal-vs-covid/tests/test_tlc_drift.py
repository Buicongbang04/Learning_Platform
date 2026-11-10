import numpy as np
import pandas as pd
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)


def raw_frame():
    t = pd.Timestamp
    return pd.DataFrame({
        "tpep_pickup_datetime": [t("2026-01-05 08:00"), t("2026-01-05 09:30"), t("2026-01-05 23:00"), t("2026-01-06 10:00"),
                                 t("2026-01-06 11:00"), t("2026-01-06 12:00"), t("2026-01-06 13:00")],
        "tpep_dropoff_datetime": [t("2026-01-05 08:12"), t("2026-01-05 09:30"), t("2026-01-05 23:20"), t("2026-01-06 09:50"),
                                  t("2026-01-06 11:30"), t("2026-01-06 15:00"), t("2026-01-06 13:10")],
        "trip_distance": [2.0, 1.0, 3.0, 1.0, 0.0, 5.0, 1.0],
        "fare_amount": [9.0, 5.0, 12.0, 6.0, 7.0, 20.0, -3.0],
        "passenger_count": [1.0, 1.0, np.nan, 2.0, 1.0, 1.0, 1.0],
        "PULocationID": [1, 2, 3, 4, 5, 6, 7],
    })


def test_prepare_adds_columns_and_applies_four_rules():
    nb = ex.notebook("tlc_drift.ipynb")
    out = nb.prepare(raw_frame())
    assert out["PULocationID"].tolist() == [1, 3]
    assert out["duration_min"].tolist() == pytest.approx([12.0, 20.0])
    assert out["hour"].tolist() == [8, 23]
    assert out.index.tolist() == [0, 1]


def test_prepare_does_not_mutate_input():
    nb = ex.notebook("tlc_drift.ipynb")
    df = raw_frame()
    nb.prepare(df)
    assert "hour" not in df.columns


def test_load_sample_columns_size_and_seed(tmp_path):
    nb = ex.notebook("tlc_drift.ipynb")
    path = tmp_path / "month.parquet"
    big = pd.DataFrame({c: range(1000) for c in nb.COLUMNS})
    big["extra_column"] = 1
    big.to_parquet(path)
    a = nb.load_sample(path, n=100, seed=0)
    b = nb.load_sample(path, n=100, seed=0)
    assert list(a.columns) == nb.COLUMNS
    assert len(a) == 100
    pd.testing.assert_frame_equal(a, b)


def test_psi_basic_properties_and_nan():
    nb = ex.notebook("tlc_drift.ipynb")
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 5000)
    assert nb.psi(x, x) == pytest.approx(0.0, abs=1e-12)
    assert nb.psi(x, rng.normal(1.0, 1, 5000)) > 0.25
    with_nan = np.r_[x, [np.nan] * 50]
    assert nb.psi(x, with_nan) == pytest.approx(0.0, abs=1e-12)


def test_psi_hand_computed_four_bins():
    nb = ex.notebook("tlc_drift.ipynb")
    reference = np.arange(100, dtype=float)
    current = np.r_[np.arange(0, 25), np.arange(0, 25), np.arange(25, 50), np.arange(75, 100)].astype(float)
    ref_share = np.array([0.25, 0.25, 0.25, 0.25])
    cur_share = np.array([0.5, 0.25, 1e-4, 0.25])
    expected = float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))
    assert nb.psi(reference, current, bins=4) == pytest.approx(expected, rel=1e-9)
    assert nb.psi(reference, reference.copy(), bins=4) == pytest.approx(0.0, abs=1e-12)


def test_psi_by_column_and_missing_share():
    nb = ex.notebook("tlc_drift.ipynb")
    rng = np.random.default_rng(1)
    a = pd.DataFrame({"trip_distance": rng.normal(0, 1, 3000), "fare_amount": rng.normal(0, 1, 3000), "hour": rng.integers(0, 24, 3000)})
    b = a.copy()
    b["fare_amount"] = b["fare_amount"] + 1.5
    out = nb.psi_by_column(a, b)
    assert list(out) == ["trip_distance", "fare_amount", "hour"]
    assert out["trip_distance"] == pytest.approx(0.0, abs=1e-12)
    assert out["fare_amount"] > 0.25
    assert nb.missing_share(pd.DataFrame({"x": [1.0, np.nan, np.nan, 4.0]}), "x") == pytest.approx(0.5)


def synthetic_trips(n, scale, seed):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "trip_distance": rng.uniform(0.5, 10, n),
        "hour": rng.integers(0, 24, n),
        "PULocationID": rng.integers(1, 30, n),
    })
    df["duration_min"] = scale * (3 + 2.0 * df["trip_distance"] + 0.1 * df["hour"])
    return df


def test_eta_mae_detects_a_changed_relationship():
    nb = ex.notebook("tlc_drift.ipynb")
    ref = synthetic_trips(4000, 1.0, 0)
    same_holdout, same_current = nb.eta_mae(ref, synthetic_trips(4000, 1.0, 1))
    _, shifted_current = nb.eta_mae(ref, synthetic_trips(4000, 1.5, 2))
    assert same_holdout < 1.0
    assert same_current < 1.0
    assert shifted_current > 5 * max(same_holdout, 0.1)


def test_real_months_psi_and_mae():
    nb = ex.notebook("tlc_drift.ipynb")
    data = {m: nb.prepare(nb.load_sample(mlopskit.real_month(ds, m))) for m, ds in nb.MONTHS.items()}
    seasonal = nb.psi_by_column(data["2019-07"], data["2019-12"])
    covid = nb.psi_by_column(data["2020-02"], data["2020-04"])
    assert max(seasonal.values()) < 0.01
    assert covid["hour"] == pytest.approx(0.152, abs=0.005)
    assert covid["fare_amount"] == pytest.approx(0.05, abs=0.005)
    assert covid["trip_distance"] == pytest.approx(0.023, abs=0.003)
    assert nb.missing_share(data["2020-04"], "passenger_count") == pytest.approx(0.082, abs=0.003)
    holdout, current = nb.eta_mae(data["2019-07"], data["2019-12"])
    assert holdout == pytest.approx(3.63, abs=0.1)
    assert current == pytest.approx(4.03, abs=0.1)
    holdout, current = nb.eta_mae(data["2020-02"], data["2020-04"])
    assert holdout == pytest.approx(3.10, abs=0.1)
    assert current == pytest.approx(5.01, abs=0.15)
