import json

import numpy as np
import pandas as pd
import pytest

import mlopskit
from testkit import Exercise

ex = Exercise(__file__)


def evidently_scores(reference, current, method, tmp_path):
    reference.to_parquet(tmp_path / "ref.parquet")
    current.to_parquet(tmp_path / "cur.parquet")
    script = (
        "import json, pandas as pd\n"
        "from evidently import Report\n"
        "from evidently.presets import DataDriftPreset\n"
        f"r = Report([DataDriftPreset(method='{method}')]).run(pd.read_parquet('cur.parquet'), pd.read_parquet('ref.parquet')).dict()\n"
        "print(json.dumps({m['config']['column']: float(m['value']) for m in r['metrics'] if 'column' in m['config']}))\n"
    )
    result = mlopskit.evidently_python(tmp_path, script)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def frames(seed=0):
    rng = np.random.default_rng(seed)
    n = 4000
    ref = pd.DataFrame({
        "gauss": rng.normal(0, 1, n),
        "skew": rng.lognormal(1, 0.8, n),
        "tail": np.r_[rng.lognormal(1, 0.5, n - 5), [9e4, 8e4, 7e4, 6e4, 5e4]],
        "small": rng.integers(0, 6, n).astype(float),
        "kind": rng.choice(["a", "b", "c"], n, p=[0.6, 0.3, 0.1]),
    })
    cur = pd.DataFrame({
        "gauss": rng.normal(0.4, 1.2, n),
        "skew": rng.lognormal(1.2, 0.8, n),
        "tail": np.r_[rng.lognormal(1.3, 0.5, n - 5), [9e4, 8e4, 7e4, 6e4, 5e4]],
        "small": rng.integers(0, 6, n).astype(float),
        "kind": rng.choice(["a", "b", "c", "d"], n, p=[0.4, 0.3, 0.1, 0.2]),
    })
    ref.loc[rng.choice(n, 100, replace=False), "gauss"] = np.nan
    cur.loc[rng.choice(n, 300, replace=False), "gauss"] = np.nan
    cur.loc[rng.choice(n, 200, replace=False), "kind"] = None
    return ref, cur


def test_psi_matches_evidently_per_column(tmp_path):
    mod = ex.module("drift_metrics.py")
    ref, cur = frames()
    expected = evidently_scores(ref, cur, "psi", tmp_path)
    for col in ref.columns:
        assert mod.psi(ref[col], cur[col]) == pytest.approx(expected[col], rel=1e-9, abs=1e-12), col


def test_ks_pvalue_matches_evidently_on_numeric_columns(tmp_path):
    mod = ex.module("drift_metrics.py")
    ref, cur = frames()
    numeric = ["gauss", "skew", "tail", "small"]
    expected = evidently_scores(ref[numeric], cur[numeric], "ks", tmp_path)
    for col in numeric:
        assert mod.ks_pvalue(ref[col], cur[col]) == pytest.approx(expected[col], rel=1e-9, abs=1e-300), col


def test_identical_samples_have_zero_psi_and_p_value_one():
    mod = ex.module("drift_metrics.py")
    x = pd.Series(np.random.default_rng(1).normal(size=2000))
    assert mod.psi(x, x) == pytest.approx(0.0, abs=1e-12)
    assert mod.ks_pvalue(x, x) == pytest.approx(1.0)


def test_zero_share_floor_rule():
    mod = ex.module("drift_metrics.py")
    shares = pd.Series([0.5, 0.0, 0.5]).to_numpy()
    assert mod._fill_zero_shares(shares)[1] == pytest.approx(1e-4)
    tiny = np.array([0.99999, 0.0, 0.00001])
    assert mod._fill_zero_shares(tiny)[1] == pytest.approx(1e-5 / 10**6)


def test_large_sample_tiny_shift_is_significant_but_not_material():
    mod = ex.module("drift_metrics.py")
    rng = np.random.default_rng(2)
    ref = pd.Series(rng.normal(0, 1, 200_000))
    cur = pd.Series(rng.normal(0.03, 1, 200_000))
    flags = mod.drift_flags(ref, cur)
    assert flags["ks_drift"] is True and flags["ks_p"] < 0.001
    assert flags["psi_drift"] is False and flags["psi"] < 0.01


def test_large_shift_is_flagged_by_both():
    mod = ex.module("drift_metrics.py")
    rng = np.random.default_rng(3)
    flags = mod.drift_flags(pd.Series(rng.normal(0, 1, 5000)), pd.Series(rng.normal(1.0, 1, 5000)))
    assert flags["psi_drift"] is True and flags["ks_drift"] is True


def test_real_month_trip_distance_matches_evidently(tmp_path):
    mod = ex.module("drift_metrics.py")
    cols = ["trip_distance"]
    jul = pd.read_parquet(mlopskit.real_month("nyc-tlc", "2019-07"), columns=cols).sample(n=50_000, random_state=0)
    dec = pd.read_parquet(mlopskit.real_month("nyc-tlc", "2019-12"), columns=cols).sample(n=50_000, random_state=0)
    expected = evidently_scores(jul, dec, "psi", tmp_path)["trip_distance"]
    assert mod.psi(jul["trip_distance"], dec["trip_distance"]) == pytest.approx(expected, rel=1e-9, abs=1e-12)
    assert mod.ks_pvalue(jul["trip_distance"], dec["trip_distance"]) < 0.05


def test_real_covid_fare_amount_equal_width_psi_is_much_lower_than_quantile_psi(tmp_path):
    mod = ex.module("drift_metrics.py")
    cols = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance", "fare_amount"]

    def prepared(dataset, month):
        df = pd.read_parquet(mlopskit.real_month(dataset, month), columns=cols).sample(n=100_000, random_state=0)
        minutes = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60
        keep = (minutes > 0) & (minutes < 180) & (df["trip_distance"] > 0) & (df["fare_amount"] > 0)
        return df.loc[keep, ["fare_amount"]].reset_index(drop=True)

    feb, apr = prepared("nyc-tlc-2020", "2020-02"), prepared("nyc-tlc-2020", "2020-04")
    expected = evidently_scores(feb, apr, "psi", tmp_path)["fare_amount"]
    assert expected == pytest.approx(0.0047, abs=0.002)
    assert mod.psi(feb["fare_amount"], apr["fare_amount"]) == pytest.approx(expected, rel=1e-9)
