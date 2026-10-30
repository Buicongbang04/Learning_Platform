import math

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
KEYS = ["yoy_growth", "best_weekday", "summer_mean", "mean_temp_c", "casual_growth", "peak_hour_mean",
        "peak_day_count", "temp_corr"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("ai_check.ipynb")


def small_day():
    return pd.DataFrame({
        "dteday": ["2011-01-01", "2011-01-02", "2011-07-01", "2012-01-01", "2012-07-01", "2012-07-02"],
        "season": [1, 1, 3, 1, 2, 2],
        "weekday": [6, 0, 5, 0, 0, 1],  # TB cnt: 6 -> 100, 0 -> 200, 5 -> 300, 1 -> 250
        "temp": [0.2, 0.3, 0.8, 0.2, 0.6, 0.7],
        "casual": [10, 20, 70, 20, 60, 50],
        "registered": [90, 80, 230, 80, 340, 200],
        "cnt": [100, 100, 300, 100, 400, 250],
    })


def small_hour():
    return pd.DataFrame({"hr": [8, 8, 17, 17, 23], "cnt": [10, 30, 25, 25, 1]})


def test_actual_values_small(nb):
    day, hour = small_day(), small_hour()
    before = day.copy()
    out = nb.actual_values(day, hour)
    pd.testing.assert_frame_equal(day, before)
    assert sorted(out) == sorted(KEYS)
    assert all(isinstance(v, float) for v in out.values())
    assert out["yoy_growth"] == pytest.approx(750 / 500 - 1)
    assert out["best_weekday"] == 5
    assert out["summer_mean"] == pytest.approx(325)
    assert out["mean_temp_c"] == pytest.approx(np.mean([0.2, 0.3, 0.8, 0.2, 0.6, 0.7]) * 41)
    assert out["casual_growth"] == pytest.approx(130 / 100 - 1)
    assert out["peak_hour_mean"] == pytest.approx(25)  # 8h: 20, 17h: 25, 23h: 1
    assert out["peak_day_count"] == pytest.approx(400)
    assert out["temp_corr"] == pytest.approx(np.corrcoef(small_day()["temp"], small_day()["cnt"])[0, 1])


def test_actual_values_datetime_input(nb):
    day = small_day()
    day["dteday"] = pd.to_datetime(day["dteday"])
    assert nb.actual_values(day, small_hour())["yoy_growth"] == pytest.approx(0.5)


def test_verify(nb):
    claims = pd.DataFrame({"claim_id": ["b", "a", "z", "c"], "text": ["", "", "", ""],
                           "claimed": [10.5, 0.649, 1.0, 0.0]})
    out = nb.verify(claims, {"a": 0.6488, "b": 10.0, "c": 0.0})
    assert list(out.columns) == ["claim_id", "claimed", "actual", "rel_error", "ok"]
    assert out["claim_id"].tolist() == ["b", "a", "z", "c"] and list(out.index) == [0, 1, 2, 3]
    assert out.loc[0, "rel_error"] == pytest.approx(0.05) and not out.loc[0, "ok"]
    assert out.loc[1, "ok"] and out.loc[1, "rel_error"] < 0.01
    assert math.isnan(out.loc[2, "actual"]) and math.isnan(out.loc[2, "rel_error"]) and not out.loc[2, "ok"]
    assert out.loc[3, "rel_error"] == 0 and out.loc[3, "ok"]
    assert out["ok"].dtype == bool


def test_verify_tolerance(nb):
    claims = pd.DataFrame({"claim_id": ["a"], "claimed": [105.0]})
    assert not nb.verify(claims, {"a": 100.0})["ok"].item()
    assert nb.verify(claims, {"a": 100.0}, rel_tol=0.05)["ok"].item()


def test_real_claims(nb):
    path = ex.dataset("bike-sharing-uci")
    day, hour = pd.read_csv(path / "day.csv"), pd.read_csv(path / "hour.csv")
    actual = nb.actual_values(day, hour)
    assert actual["yoy_growth"] == pytest.approx(0.6488, abs=1e-4)
    assert actual["best_weekday"] == 5
    assert actual["summer_mean"] == pytest.approx(4992.33, abs=0.01)
    assert actual["mean_temp_c"] == pytest.approx(20.31, abs=0.01)
    assert actual["casual_growth"] == pytest.approx(0.5076, abs=1e-4)
    assert actual["peak_hour_mean"] == pytest.approx(461.45, abs=0.01)
    assert actual["peak_day_count"] == 8714
    assert actual["temp_corr"] == pytest.approx(0.6275, abs=1e-4)
    report = nb.verify(nb.LLM_CLAIMS, actual)
    assert dict(zip(report["claim_id"], report["ok"])) == {
        "yoy_growth": True, "best_weekday": False, "summer_mean": False, "mean_temp_c": False,
        "casual_growth": False, "peak_hour_mean": True, "peak_day_count": True, "temp_corr": True}


def orders():
    return pd.DataFrame({
        "Invoice": ["536365", "536366", "536367"],
        "Customer ID": [17850.0, np.nan, 13047.0],
        "Email": ["a@x.com", "b@y.com", None],
        "customer_name": ["An", "Bình", "Chi"],
        "Country": ["United Kingdom", "France", "United Kingdom"],
        "Price": [2.55, np.nan, 3.39],
        "Phone Number": ["0901", "0902", "0903"],
        "Note": [None, None, None],
    })


def test_safe_profile_structure(nb):
    df = orders()
    before = df.copy()
    out = nb.llm_safe_profile(df)
    pd.testing.assert_frame_equal(df, before)
    assert list(out.index) == list(df.columns)
    assert list(out.columns) == ["dtype", "missing", "unique", "example"]
    assert out.loc["Customer ID", "dtype"] == "float64"
    assert out.loc["Price", "missing"] == 1 and out.loc["Price", "unique"] == 2
    assert out.loc["Note", "missing"] == 3 and out.loc["Note", "unique"] == 0 and out.loc["Note", "example"] == ""


def test_safe_profile_redacts(nb):
    out = nb.llm_safe_profile(orders(), sensitive=["Country"])
    redacted = {c for c in out.index if out.loc[c, "example"] == nb.REDACTED}
    assert redacted == {"Customer ID", "Email", "customer_name", "Phone Number", "Country"}
    assert out.loc["Invoice", "example"] == "536365"
    assert out.loc["Price", "example"] == "2.55"
    flat = out.to_string()
    for secret in ["17850", "a@x.com", "An ", "0901", "United Kingdom"]:
        assert secret not in flat, f"Lộ giá trị nhạy cảm: {secret}"


def test_safe_profile_unknown_sensitive_column(nb):
    with pytest.raises(ValueError):
        nb.llm_safe_profile(orders(), sensitive=["Customer_ID"])
